import os
import cv2
import numpy as np
from .utility import util

class helios:
    """
    Set of convenience functions for the Helios SEM.
    """
    def __init__(self,filename):
        """
        initialize class by loading the file

        Parameters
        ----------
        filename : string
            name of the file to load. Can but is not required to include .tif
            as extension.


        Returns
        -------
        None.

        """
        
        #raise error if wrong format or file does not exist
        if type(filename) != str:
            raise TypeError('The argument to the helios class must be a string containing the filename.')
        if not os.path.exists(filename):
            if os.path.exists(filename + '.tif'):
                filename = filename + '.tif'
            else:
                raise FileNotFoundError('The file "'+filename+'" could not be found.')
            
        self.filename = filename
    
    def load_image(self):
        """
        load the image and split into image and databar

        Returns
        -------
        numpy.array
            array of pixel values in the image (not including the data bar)

        """
        im = cv2.imread(self.filename,0)
        self.shape = np.shape(im)
        self.image = im[:int(self.shape[1]/1.5)]
        if int(self.shape[1]/1.5) < self.shape[0]:
            self.databar = im[int(self.shape[1]/1.5):]
        else:
            self.databar = None
        return self.image
    
    def load_metadata(self):
        """
        Load the metadata footer from Helios SEM files and return xml tree
        object which can be indexed for extraction of useful parameters. Does
        not require loading whole file into memory. Attempts first to find xml
        formatted data, if this is not found it looks for 'human' formatted
        metadata.

        Returns
        -------
        xml.etree.ElementTree root object
            xml root object of the metadata. Can be printed using it as
            argument to print_metadata, or indexed with
            xml_root.find('<element name>').

        """
        import io
        import xml.etree.ElementTree as et
        
        metadata = ''
        read = False
        
        #for slice and view images the metadata is already in xml format
        try:
            with io.open(self.filename, 'r', errors='ignore', encoding='utf8') as file:
                #read file line by line to avoid loading too much into memory
                for line in file:
                    #start reading at the first line containing an xml tag
                    if '<?xml' in line:
                        read = True
                    if read:
                        metadata += line
                        if '</Metadata>' in line:
                            break #stop at line with end tag
            
            #trim strings down to only xml
            metadata = metadata[metadata.find('<?xml'):]
            metadata = metadata[:metadata.find('</Metadata>')+11]
            
            self.metadata = et.fromstring(metadata)
            return self.metadata
        
        #otherwise construct the metadata from formatted metadata in file
        except:
            with io.open(self.filename, 'r', errors='ignore', encoding='utf8') as file:
                for line in file:
                    #start reading at first line with [User], break at next \x00
                    if read:
                        metadata += line
                        if '\x00' in line:
                            break
                    if '[User]' in line:
                        read = True
                        metadata += line
            
            metadata = metadata[metadata.find('[User]'):]
            metadata = metadata[:metadata.find('\x00')-2]
            metadata = metadata.split('\n')
            
            #construct xml object
            xml_root = et.Element('MetaData')
            for line in metadata:
                if line != '':
                    if line[0] == '[':
                        child = et.SubElement(xml_root,line[1:-1])
                    else:
                        line = line.split('=')
                        subchild = et.SubElement(child,line[0])
                        subchild.text = line[1]
            
            self.metadata = xml_root
            return xml_root
    
    def print_metadata(self):
        """print formatted output of metadata"""
        
        try:
            xml_root = self.metadata
        except AttributeError:
            xml_root = self.load_metadata()
        
        util.print_metadata(xml_root)
        
        
    def get_pixelsize(self):
        """
        gets the pixel size from the metadata and calculates the unit

        Returns
        -------
        pixelsize : float
            the pixelsize in calibrated (physical) units
        unit : string
            the physical unit of the pixel size

        """
        #get the metadata or load it if it is not (yet) available
        try:
            xml_root = self.metadata
        except AttributeError:
            xml_root = self.load_metadata()
        
        #find the pixelsize (may be two different formats)
        try:
            pixelsize_x = float(xml_root.find('Scan').find('PixelWidth').text)
            pixelsize_y = float(xml_root.find('Scan').find('PixelHeight').text)
        except:
            pixelsize_x = float(xml_root.find('BinaryResult').find('PixelSize').find('X').text)
            pixelsize_y = float(xml_root.find('BinaryResult').find('PixelSize').find('Y').text)
        
        #find the right unit and rescale for convenience
        if pixelsize_x >= 0.1:
            unit = 'm'
        elif pixelsize_x < 0.1 and pixelsize_x >= 0.1e-3:
            unit = 'mm'
            pixelsize_x,pixelsize_y = 1e3*pixelsize_x,1e3*pixelsize_y
        elif pixelsize_x < 0.1e-3 and pixelsize_x >= 0.1e-6:
            unit = 'µm'
            pixelsize_x,pixelsize_y = 1e6*pixelsize_x,1e6*pixelsize_y
        else:
            unit = 'nm'
            pixelsize_x,pixelsize_y = 1e9*pixelsize_x,1e9*pixelsize_y
        
        pixelsize = (pixelsize_x,pixelsize_y)
        print('Pixel size x: {:.6g}'.format(pixelsize[0]),unit)
        print('Pixel size y: {:.6g}'.format(pixelsize[1]),unit)
        
        self.pixelsize= pixelsize
        self.unit = unit
        
        return pixelsize,unit
    
    def export_with_scalebar(self,filename=None,barsize=None,crop=None,scale=1,
                             loc=2,resolution=None,box=True,invert=False):
        """
        saves an exported image of the TEM image with a scalebar in one of the 
        four corners, where barsize is the scalebar size in data units (e.g. 
        nm) and scale the overall scaling of the scalebar and text on the image

        Parameters
        ----------
        filename : string or None, optional
            Filename + extension to use for the export file. The default is the
            filename sans extension of the original TEM file, with 
            '_exported.png' appended.
        barsize : float or None, optional
            size (in data units matching the original scale bar, e.g. nm) of 
            the scale bar to use. The default is the same as the original bar.
        crop : tuple of form `((xmin,ymin),(xmax,ymax))` or None, optional
            range describing a area of the original image (before rescaling the
            resolution) to crop out for the export image. The default is None 
            which takes the entire image.
        scale : float, optional
            factor to change the size of the scalebar+text with respect to the
            width of the image. The default is 1.
        loc : int, one of [`0`,`1`,`2`,`3`], optional
            Location of the scalebar on the image, where 0, 1, 2 and 3 refer to
            the top left, top right, bottom left and bottom right respectively.
            The default is 2, which is the bottom left corner.
        resolution : int, optional
            the resolution along the x-axis (i.e. image width in pixels) to use
            for the exported image. The default is None, which uses the size of
            the original image.
        box : bool, optional
            Whether to put a semitransparent box around the scalebar and text
            to enhance contrast. The default is True.
        invert : bool, optional
            If True, a white scalebar and text on a black box are used. The 
            default is False which gives black text on a white background.
        """
        #imports
        import matplotlib.pyplot as plt
        from PIL import ImageFont, ImageDraw, Image
        
        #check if pixelsize already calculated, otherwise call get_pixelsize
        try:
            pixelsize,unit = self.pixelsize,self.unit
        except AttributeError:
            pixelsize,unit = self.get_pixelsize()
        
        #set default export filename
        if type(filename) != str:
            filename = self.filename[:-4]+'_scalebar.png'
        
        #check we're not overwriting the original file
        if filename==self.filename:
            raise ValueError('overwriting original SEM file not reccomended, '+
                             'use a different filename for exporting.')
              
        #get and display image
        try:
            exportim = self.image.copy()
        except AttributeError:
            exportim = self.load_image()
        
        #show original figure
        fig,ax = plt.subplots(1,1)
        ax.imshow(exportim,cmap='gray',vmin=0,vmax=255)
        plt.title('original image')
        plt.axis('off')
        plt.tight_layout()
        
        #print current axes limits for easy cropping
        def _on_lim_change(call):
            [txt.set_visible(False) for txt in ax.texts]
            xmin,xmax = ax.get_xlim()
            ymax,ymin = ax.get_ylim()
            croptext = 'current crop: (({:}, {:}), ({:}, {:}))'
            croptext = croptext.format(int(xmin),int(ymin),int(xmax+1),int(ymax+1))
            ax.text(0.01,0.01,croptext,fontsize=12,ha='left',va='bottom',
                    transform=ax.transAxes,color='red')
        
        #attach callback to limit change
        ax.callbacks.connect("xlim_changed", _on_lim_change)
        ax.callbacks.connect("ylim_changed", _on_lim_change)
        
        #(optionally) crop the image
        if type(crop) != type(None):
            exportim = exportim[crop[0][1]:crop[1][1],crop[0][0]:crop[1][0]]
        
        #set default scalebar to original scalebar or calculate len
        if type(barsize) == type(None):
            #take 15% of image width and round to nearest in list of 'nice' vals
            barsize = 0.15*exportim.shape[1]*pixelsize[0]
            lst = [0.1,0.2,0.3,0.4,0.5,0.6,0.8,1,2,2.5,3,4,5,6,8,10,20,25,30,
                   40,50,60,80,100,200,250,300,400,500,600,800,1000,2000,2500,
                   3000,4000,5000,6000,8000,10000]
            barsize = lst[min(range(len(lst)), key=lambda i: abs(lst[i]-barsize))]
            barsize_px = barsize/pixelsize[0]
            
        else:
            barsize_px = barsize/pixelsize[0]
        
        #set default resolution or scale image and correct barsize_px
        if type(resolution) == type(None):
            ny,nx = exportim.shape
            resolution = nx
        else:
            nx = resolution
            ny = int(exportim.shape[0]/exportim.shape[1]*nx)
            barsize_px = barsize_px/exportim.shape[1]*resolution
            exportim = cv2.resize(exportim, (int(nx),int(ny)), interpolation=cv2.INTER_AREA)
        
        
        #adjust general scaling for all sizes relative to 1024 pixels
        scale = scale*resolution/1024
        
        #set up sizes
        barheight = scale*16
        boxpad = scale*10
        barpad = scale*10
        textpad = scale*2
        font = 'verdana.ttf'
        fontsize = 32*scale
        
        #format string
        if round(barsize)==barsize:
            text = str(int(barsize))+' '+unit
        else:
            for i in range(1,4):
                if round(barsize,i)==barsize:
                    text = ('{:.'+str(i)+'f} ').format(barsize)+unit
                    break
                elif i==3:
                    text = '{:.3f} '.format(round(barsize,3))+unit
        
        #get size of text
        #textsize = cv2.getTextSize(text, font, fontsize, int(fontthickness))[0]
        font = ImageFont.truetype(font,size=int(fontsize))
        textsize = ImageDraw.Draw(Image.fromarray(exportim)).textsize(text,font=font)
        offset = font.getoffset(text)
        textsize = (textsize[0]+offset[0],textsize[1]+offset[1])    
        
        #correct baseling for mu in case of micrometer
        if unit=='µm':
            textsize = (textsize[0],textsize[1]-6*scale)
        
        #determine box size
        boxheight = barpad + barheight + 2*textpad + textsize[1]
        
        #determine box position based on loc
        #top left
        if loc == 0:
            x = boxpad
            y = boxpad
        #top right
        elif loc == 1:
            x = nx - boxpad - 2*barpad - max([barsize_px,textsize[0]])
            y = boxpad
        #bottom left
        elif loc == 2:
            x = boxpad
            y = ny - boxpad - boxheight
        #bottom right
        elif loc == 3:
            x = nx - boxpad - 2*barpad - max([barsize_px,textsize[0]])
            y = ny - boxpad - boxheight
        else:
            raise ValueError("loc must be 0, 1, 2 or 3 for top left, top right"+
                             ", bottom left or bottom right respectively.")
        
        #put semitransparent box
        if box:
            #get rectangle from im and create box
            w,h = 2*barpad+max([barsize_px,textsize[0]]),boxheight
            subim = exportim[int(y):int(y+h), int(x):int(x+w)]
            white_box = np.ones(subim.shape, dtype=np.uint8) * 255
            
            #add or subtract box from im, and put back in im
            if invert:
                exportim[int(y):int(y+h), int(x):int(x+w)] = \
                    cv2.addWeighted(subim, 0.5, -white_box, 0.5, 1.0)
            else:
                exportim[int(y):int(y+h), int(x):int(x+w)] = \
                    cv2.addWeighted(subim, 0.5, white_box, 0.5, 1.0)

        #calculate positions for bar and text (horizontally centered in box)
        barx = (2*x + 2*barpad + max([barsize_px,textsize[0]]))/2 - barsize_px/2
        bary = y+boxheight-barpad-barheight
        textx = (2*x + 2*barpad + max([barsize_px,textsize[0]]))/2 - textsize[0]/2
        texty = y + textpad
        
        #color for bar and text
        if invert:
            color = 255
        else:
            color = 0
        
        #draw scalebar
        exportim = cv2.rectangle(
            exportim,
            (int(barx),int(bary)),
            (int(barx+barsize_px),int(bary+barheight)),
            color,
            -1
        )
        
        #draw text
        exportim = Image.fromarray(exportim)
        draw = ImageDraw.Draw(exportim)
        draw.text(
            (textx,texty),
            text,
            fill=color,
            font=font
        )
        exportim = np.array(exportim)
        
        #show result
        plt.figure()
        plt.imshow(exportim,cmap='gray',vmin=0,vmax=255)
        plt.title('exported image')
        plt.axis('off')
        plt.tight_layout()
        
        #save image
        cv2.imwrite(filename,exportim)


#==============================================================================
# PHENOM
#==============================================================================
class phenom:
    """
    Set of convenience functions for the phenom SEM microscopes.
    """
    def __init__(self,filename):
        """Initialize the class instance"""
        
        #raise error if wrong format or file does not exist
        if type(filename) != str:
            raise TypeError('The argument to the helios class must be a string containing the filename.')
        if not os.path.exists(filename):
            raise FileNotFoundError('The file "'+filename+'" could not be found.')
            
        self.filename = filename
    
    def load_image(self):
        """load the image and split into image and databar"""
        im = cv2.imread(self.filename,0)
        self.shape = np.shape(im)
        self.image = im[:int(self.shape[1])]
        self.databar = im[int(self.shape[1]):]
        return self.image
    
    def load_metadata(self):
        """Load the metadata footer from Helios SEM files and return xml tree
        object which can be indexed for extraction of useful parameters. Does
        not require loading whole file into memory. Attempts first to find xml
        formatted data, if this is not found it looks for 'human' formatted
        metadata.
        

        Returns
        -------
        xml.etree.ElementTree object
            xml root object of the metadata. Can be printed using it as
            argument to print_metadata, or indexed with
            xml_root.find('<element name>')
        """
        import io
        import xml.etree.ElementTree as et
        
        metadata = ''
        read = False
        
        #for slice and view images the metadata is already in xml format
        with io.open(self.filename, 'r', errors='ignore', encoding='utf8') as file:
            #read file line by line to avoid loading too much into memory
            for line in file:
                #start reading at the first line containing an xml tag
                if '<?xml' in line:
                    read = True
                if read:
                    metadata += line
                    if '</FeiImage>' in line:
                        break #stop at line with end tag
            
        #trim strings down to only xml
        metadata = metadata[metadata.find('<?xml'):]
        metadata = metadata[:metadata.find('</FeiImage>')+11]
        
        self.metadata = et.fromstring(metadata)
        return self.metadata
        

    def print_metadata(self):
        """print formatted output of metadata"""
        
        try:
            xml_root = self.metadata
        except AttributeError:
            xml_root = self.load_metadata()
        
        util.print_metadata(xml_root)
    
    
    def get_pixelsize(self):
        """gets the pixel size from the metadata and calculates the unit

        Returns
        -------
        pixelsize : (y,x) tuple of float
            physical size of the pixels
        unit : str
            physical unit corresponding to the pixelsize.

        """      
        #get the metadata or load it if it is not (yet) available
        try:
            xml_root = self.metadata
        except AttributeError:
            xml_root = self.load_metadata()
        
        #find the pixelsize (may be two different formats)
        pixelsize_x = float(xml_root.find('pixelWidth').text)
        pixelsize_y = float(xml_root.find('pixelHeight').text)
        
        #get the unit
        if xml_root.find('pixelWidth').attrib['unit'] != xml_root.find('pixelHeight').attrib['unit']:
            print('[WARNING] Unit for x and y not the same, using x unit')
        unit = xml_root.find('pixelWidth').attrib['unit']
        if unit == 'um':
            unit = 'µm'
        
        #print result
        pixelsize = (pixelsize_y,pixelsize_x)
        print('Pixel size x: {:.6g}'.format(pixelsize[0]),unit)
        print('Pixel size y: {:.6g}'.format(pixelsize[1]),unit)
        
        self.pixelsize= pixelsize
        self.unit = unit
        
        return pixelsize,unit

    def export_with_scalebar(self,filename=None,barsize=None,crop=None,scale=1,
                             loc=2,resolution=None,box=True,invert=False):
        """
        saves an exported image of the TEM image with a scalebar in one of the 
        four corners, where barsize is the scalebar size in data units (e.g. 
        nm) and scale the overall scaling of the scalebar and text on the image

        Parameters
        ----------
        filename : string or None, optional
            Filename + extension to use for the export file. The default is the
            filename sans extension of the original TEM file, with 
            '_exported.png' appended.
        barsize : float or None, optional
            size (in data units matching the original scale bar, e.g. nm) of 
            the scale bar to use. The default is the same as the original bar.
        crop : tuple of form `((xmin,ymin),(xmax,ymax))` or None, optional
            range describing a area of the original image (before rescaling the
            resolution) to crop out for the export image. The default is None 
            which takes the entire image.
        scale : float, optional
            factor to change the size of the scalebar+text with respect to the
            width of the image. The default is 1.
        loc : int, one of [`0`,`1`,`2`,`3`], optional
            Location of the scalebar on the image, where 0, 1, 2 and 3 refer to
            the top left, top right, bottom left and bottom right respectively.
            The default is 2, which is the bottom left corner.
        resolution : int, optional
            the resolution along the x-axis (i.e. image width in pixels) to use
            for the exported image. The default is None, which uses the size of
            the original image.
        box : bool, optional
            Whether to put a semitransparent box around the scalebar and text
            to enhance contrast. The default is True.
        invert : bool, optional
            If True, a white scalebar and text on a black box are used. The 
            default is False which gives black text on a white background.
        """
        #imports
        import matplotlib.pyplot as plt
        from PIL import ImageFont, ImageDraw, Image
        
        #check if pixelsize already calculated, otherwise call get_pixelsize
        try:
            pixelsize,unit = self.pixelsize,self.unit
        except AttributeError:
            pixelsize,unit = self.get_pixelsize()
        
        #set default export filename
        if type(filename) != str:
            filename = self.filename[:-4]+'_scalebar.png'
        
        #check we're not overwriting the original file
        if filename==self.filename:
            raise ValueError('overwriting original SEM file not reccomended, '+
                             'use a different filename for exporting.')
              
        #get and display image
        try:
            exportim = self.image.copy()
        except AttributeError:
            exportim = self.load_image()
        
        #show original figure
        fig,ax = plt.subplots(1,1)
        ax.imshow(exportim,cmap='gray',vmin=0,vmax=255)
        plt.title('original image')
        plt.axis('off')
        plt.tight_layout()
        
        #print current axes limits for easy cropping
        def _on_lim_change(call):
            [txt.set_visible(False) for txt in ax.texts]
            xmin,xmax = ax.get_xlim()
            ymax,ymin = ax.get_ylim()
            croptext = 'current crop: (({:}, {:}), ({:}, {:}))'
            croptext = croptext.format(int(xmin),int(ymin),int(xmax+1),int(ymax+1))
            ax.text(0.01,0.01,croptext,fontsize=12,ha='left',va='bottom',
                    transform=ax.transAxes,color='red')
        
        #attach callback to limit change
        ax.callbacks.connect("xlim_changed", _on_lim_change)
        ax.callbacks.connect("ylim_changed", _on_lim_change)
        
        #(optionally) crop
        if type(crop) != type(None):
            exportim = exportim[crop[0][1]:crop[1][1],crop[0][0]:crop[1][0]]
        
        #set default scalebar to original scalebar or calculate len
        if type(barsize) == type(None):
            #take 15% of image width and round to nearest in list of 'nice' vals
            barsize = 0.15*exportim.shape[1]*pixelsize[0]
            lst = [0.1,0.2,0.3,0.4,0.5,0.6,0.8,1,2,2.5,3,4,5,6,8,10,20,25,30,
                   40,50,60,80,100,200,250,300,400,500,600,800,1000,2000,2500,
                   3000,4000,5000,6000,8000,10000]
            barsize = lst[min(range(len(lst)), key = lambda i: abs(lst[i]-barsize))]
            barsize_px = barsize/pixelsize[0]
            
        else:
            barsize_px = barsize/pixelsize[0]
        
        #set default resolution or scale image and correct barsize_px
        if type(resolution) == type(None):
            ny,nx = exportim.shape
            resolution = nx
        else:
            nx = resolution
            ny = int(exportim.shape[0]/exportim.shape[1]*nx)
            barsize_px = barsize_px/exportim.shape[1]*resolution
            exportim = cv2.resize(exportim, (int(nx),int(ny)), interpolation=cv2.INTER_AREA)
        
        
        #adjust general scaling for all sizes relative to 1024 pixels
        scale = scale*resolution/1024
        
        #set up sizes
        barheight = scale*16
        boxpad = scale*10
        barpad = scale*10
        textpad = scale*2
        font = 'verdana.ttf'
        fontsize = 32*scale
        
        #format string
        if round(barsize)==barsize:
            text = str(int(barsize))+' '+unit
        else:
            for i in range(1,4):
                if round(barsize,i)==barsize:
                    text = ('{:.'+str(i)+'f} ').format(barsize)+unit
                    break
                elif i==3:
                    text = '{:.3f} '.format(round(barsize,3))+unit
        
        #get size of text
        #textsize = cv2.getTextSize(text, font, fontsize, int(fontthickness))[0]
        font = ImageFont.truetype(font,size=int(fontsize))
        textsize = ImageDraw.Draw(Image.fromarray(exportim)).textsize(text,font=font)
        offset = font.getoffset(text)
        textsize = (textsize[0]+offset[0],textsize[1]+offset[1])    
        
        #correct baseling for mu in case of micrometer
        if unit=='µm':
            textsize = (textsize[0],textsize[1]-6*scale)
        
        #determine box size
        boxheight = barpad + barheight + 2*textpad + textsize[1]
        
        #determine box position based on loc
        #top left
        if loc == 0:
            x = boxpad
            y = boxpad
        #top right
        elif loc == 1:
            x = nx - boxpad - 2*barpad - max([barsize_px,textsize[0]])
            y = boxpad
        #bottom left
        elif loc == 2:
            x = boxpad
            y = ny - boxpad - boxheight
        #bottom right
        elif loc == 3:
            x = nx - boxpad - 2*barpad - max([barsize_px,textsize[0]])
            y = ny - boxpad - boxheight
        else:
            raise ValueError("loc must be 0, 1, 2 or 3 for top left, top right"+
                             ", bottom left or bottom right respectively.")
        
        #put semitransparent box
        if box:
            #get rectangle from im and create box
            w,h = 2*barpad+max([barsize_px,textsize[0]]),boxheight
            subim = exportim[int(y):int(y+h), int(x):int(x+w)]
            white_box = np.ones(subim.shape, dtype=np.uint8) * 255
            
            #add or subtract box from im, and put back in im
            if invert:
                exportim[int(y):int(y+h), int(x):int(x+w)] = \
                    cv2.addWeighted(subim, 0.5, -white_box, 0.5, 1.0)
            else:
                exportim[int(y):int(y+h), int(x):int(x+w)] = \
                    cv2.addWeighted(subim, 0.5, white_box, 0.5, 1.0)

        #calculate positions for bar and text (horizontally centered in box)
        barx = (2*x + 2*barpad + max([barsize_px,textsize[0]]))/2 - barsize_px/2
        bary = y+boxheight-barpad-barheight
        textx = (2*x + 2*barpad + max([barsize_px,textsize[0]]))/2 - textsize[0]/2
        texty = y + textpad
        
        #color for bar and text
        if invert:
            color = 255
        else:
            color = 0
        
        #draw scalebar
        exportim = cv2.rectangle(
            exportim,
            (int(barx),int(bary)),
            (int(barx+barsize_px),int(bary+barheight)),
            color,
            -1
        )
        
        #draw text
        exportim = Image.fromarray(exportim)
        draw = ImageDraw.Draw(exportim)
        draw.text(
            (textx,texty),
            text,
            fill=color,
            font=font
        )
        exportim = np.array(exportim)
        
        #show result
        plt.figure()
        plt.imshow(exportim,cmap='gray',vmin=0,vmax=255)
        plt.title('exported image')
        plt.axis('off')
        plt.tight_layout()
        
        #save image
        cv2.imwrite(filename,exportim)


class xl30sfeg:
    """
    Set of convenience functions for the xl30sfeg SEM microscope.
    """
    def __init__(self,filename):
        """initialize class by storing the file name"""
        
        #raise error if wrong format or file does not exist
        if type(filename) != str:
            raise TypeError('The argument to the xl30sfeg class must be a string containing the filename.')
        if not os.path.exists(filename):
            raise FileNotFoundError('The file "'+filename+'" could not be found.')
        
        self.filename = filename
    
    def load_image(self):
        """load the image and (if present) scalebar"""
        im = cv2.imread(self.filename,0)
        
        self.shape = np.shape(im)
        self.image = im[:int(self.shape[1]/1.330)]
        
        #check if scalebar is present
        if len(im) > int(self.shape[1]/1.330):
            self.scalebar = im[int(self.shape[1]/1.330):]
        
        return self.image
    
    
    def load_metadata(self):
        """Load the metadata footer from XL30SFEG SEM files and return xml tree
        object which can be indexed for extraction of useful parameters. Does 
        not require loading whole file into memory. Searches for 'human' 
        formatted metadata.

        Returns
        -------
        xml_root : xml.etree.ElementTree object
            xml root object of the metadata. Can be printed using it as
            argument to print_metadata, or indexed with
            xml_root.find('<element name>')

        """
        import xml.etree.ElementTree as et
        import io
        
        metadata = ''
        read = False
         
        #construct the metadata from formatted metadata in file
        with io.open(self.filename, 'r', errors='ignore', encoding='utf8') as file:
            for line in file:
                #start reading at first line with [DatabarData], break at last item
                if read:
                    metadata += line
                    if 'IonBright3' in line:
                        break
                if '[DatabarData]' in line:
                    read = True
                    metadata += line
        
        metadata = metadata[metadata.find('[DatabarData]'):]
        metadata = metadata.split("\n")
        
        #construct xml object
        xml_root = et.Element('MetaData')
        for line in metadata:
            if line != '':
                if line[0] == '[':
                    child = et.SubElement(xml_root,line[1:-1].strip())
                else:
                    line = line.split('=')
                    subchild = et.SubElement(child,line[0].strip())
                    subchild.text = line[1].strip()
        
        self.metadata = xml_root
        return xml_root
    
    def print_metadata(self):
        """print formatted output of metadata"""
        
        try:
            xml_root = self.metadata
        except AttributeError:
            xml_root = self.load_metadata()
        
        util.print_metadata(xml_root)
    
    def get_pixelsize(self):
        """gets the pixel size from the metadata and calculates the unit

        Returns
        -------
        pixelsize : float
            physical size of the pixels in x and y
        unit : str
            physical unit corresponding to the pixelsize.

        """   
        #try finding metadata, else call load_metadata
        try:
            self.metadata
        except AttributeError:
            self.load_metadata()
        
        
        self.pixelsize = float(self.metadata.find('DatabarData').find('flMagn').text)
        self.unit = 'µm'
        
        return self.pixelsize,self.unit

    def export_with_scalebar(self,filename=None,barsize=None,crop=None,scale=1,
                             loc=2,resolution=None,box=True,invert=False):
        """
        saves an exported image of the TEM image with a scalebar in one of the 
        four corners, where barsize is the scalebar size in data units (e.g. 
        nm) and scale the overall scaling of the scalebar and text on the image

        Parameters
        ----------
        filename : string or None, optional
            Filename + extension to use for the export file. The default is the
            filename sans extension of the original TEM file, with 
            '_exported.png' appended.
        barsize : float or None, optional
            size (in data units matching the original scale bar, e.g. nm) of 
            the scale bar to use. The default is the same as the original bar.
        crop : tuple of form `((xmin,ymin),(xmax,ymax))` or None, optional
            range describing a area of the original image (before rescaling the
            resolution) to crop out for the export image. The default is None 
            which takes the entire image.
        scale : float, optional
            factor to change the size of the scalebar+text with respect to the
            width of the image. The default is 1.
        loc : int, one of [`0`,`1`,`2`,`3`], optional
            Location of the scalebar on the image, where 0, 1, 2 and 3 refer to
            the top left, top right, bottom left and bottom right respectively.
            The default is 2, which is the bottom left corner.
        resolution : int, optional
            the resolution along the x-axis (i.e. image width in pixels) to use
            for the exported image. The default is None, which uses the size of
            the original image.
        box : bool, optional
            Whether to put a semitransparent box around the scalebar and text
            to enhance contrast. The default is True.
        invert : bool, optional
            If True, a white scalebar and text on a black box are used. The 
            default is False which gives black text on a white background.
        """
        #imports
        import matplotlib.pyplot as plt
        from PIL import ImageFont, ImageDraw, Image
        
        #check if pixelsize already calculated, otherwise call get_pixelsize
        try:
            pixelsize,unit = self.pixelsize,self.unit
        except AttributeError:
            pixelsize,unit = self.get_pixelsize()
        
        #set default export filename
        if type(filename) != str:
            filename = self.filename[:-4]+'_scalebar.png'
        
        #check we're not overwriting the original file
        if filename==self.filename:
            raise ValueError('overwriting original SEM file not reccomended, '+
                             'use a different filename for exporting.')
              
        #get and display image
        try:
            exportim = self.image.copy()
        except AttributeError:
            exportim = self.load_image()
        
        #show original figure
        fig,ax = plt.subplots(1,1)
        ax.imshow(exportim,cmap='gray',vmin=0,vmax=255)
        plt.title('original image')
        plt.axis('off')
        plt.tight_layout()
        
        #print current axes limits for easy cropping
        def _on_lim_change(call):
            [txt.set_visible(False) for txt in ax.texts]
            xmin,xmax = ax.get_xlim()
            ymax,ymin = ax.get_ylim()
            croptext = 'current crop: (({:}, {:}), ({:}, {:}))'
            croptext = croptext.format(int(xmin),int(ymin),int(xmax+1),int(ymax+1))
            ax.text(0.01,0.01,croptext,fontsize=12,ha='left',va='bottom',
                    transform=ax.transAxes,color='red')
        
        #attach callback to limit change
        ax.callbacks.connect("xlim_changed", _on_lim_change)
        ax.callbacks.connect("ylim_changed", _on_lim_change)
        
        #(optionally) crop
        if type(crop) != type(None):
            exportim = exportim[crop[0][1]:crop[1][1],crop[0][0]:crop[1][0]]
        
        #set default scalebar to original scalebar or calculate len
        if type(barsize) == type(None):
            #take 15% of image width and round to nearest in list of 'nice' vals
            barsize = 0.15*exportim.shape[1]*pixelsize[0]
            lst = [0.1,0.2,0.3,0.4,0.5,0.6,0.8,1,2,2.5,3,4,5,6,8,10,20,25,30,
                   40,50,60,80,100,200,250,300,400,500,600,800,1000,2000,2500,
                   3000,4000,5000,6000,8000,10000]
            barsize = lst[min(range(len(lst)), key = lambda i: abs(lst[i]-barsize))]
            barsize_px = barsize/pixelsize[0]
            
        else:
            barsize_px = barsize/pixelsize[0]
        
        #set default resolution or scale image and correct barsize_px
        if type(resolution) == type(None):
            ny,nx = exportim.shape
            resolution = nx
        else:
            nx = resolution
            ny = int(exportim.shape[0]/exportim.shape[1]*nx)
            barsize_px = barsize_px/exportim.shape[1]*resolution
            exportim = cv2.resize(exportim, (int(nx),int(ny)), interpolation=cv2.INTER_AREA)
        
        
        #adjust general scaling for all sizes relative to 1024 pixels
        scale = scale*resolution/1024
        
        #set up sizes
        barheight = scale*16
        boxpad = scale*10
        barpad = scale*10
        textpad = scale*2
        font = 'verdana.ttf'
        fontsize = 32*scale
        
        #format string
        if round(barsize)==barsize:
            text = str(int(barsize))+' '+unit
        else:
            for i in range(1,4):
                if round(barsize,i)==barsize:
                    text = ('{:.'+str(i)+'f} ').format(barsize)+unit
                    break
                elif i==3:
                    text = '{:.3f} '.format(round(barsize,3))+unit
        
        #get size of text
        #textsize = cv2.getTextSize(text, font, fontsize, int(fontthickness))[0]
        font = ImageFont.truetype(font,size=int(fontsize))
        textsize = ImageDraw.Draw(Image.fromarray(exportim)).textsize(text,font=font)
        offset = font.getoffset(text)
        textsize = (textsize[0]+offset[0],textsize[1]+offset[1])    
        
        #correct baseling for mu in case of micrometer
        if unit=='µm':
            textsize = (textsize[0],textsize[1]-6*scale)
        
        #determine box size
        boxheight = barpad + barheight + 2*textpad + textsize[1]
        
        #determine box position based on loc
        #top left
        if loc == 0:
            x = boxpad
            y = boxpad
        #top right
        elif loc == 1:
            x = nx - boxpad - 2*barpad - max([barsize_px,textsize[0]])
            y = boxpad
        #bottom left
        elif loc == 2:
            x = boxpad
            y = ny - boxpad - boxheight
        #bottom right
        elif loc == 3:
            x = nx - boxpad - 2*barpad - max([barsize_px,textsize[0]])
            y = ny - boxpad - boxheight
        else:
            raise ValueError("loc must be 0, 1, 2 or 3 for top left, top right"+
                             ", bottom left or bottom right respectively.")
        
        #put semitransparent box
        if box:
            #get rectangle from im and create box
            w,h = 2*barpad+max([barsize_px,textsize[0]]),boxheight
            subim = exportim[int(y):int(y+h), int(x):int(x+w)]
            white_box = np.ones(subim.shape, dtype=np.uint8) * 255
            
            #add or subtract box from im, and put back in im
            if invert:
                exportim[int(y):int(y+h), int(x):int(x+w)] = \
                    cv2.addWeighted(subim, 0.5, -white_box, 0.5, 1.0)
            else:
                exportim[int(y):int(y+h), int(x):int(x+w)] = \
                    cv2.addWeighted(subim, 0.5, white_box, 0.5, 1.0)

        #calculate positions for bar and text (horizontally centered in box)
        barx = (2*x + 2*barpad + max([barsize_px,textsize[0]]))/2 - barsize_px/2
        bary = y+boxheight-barpad-barheight
        textx = (2*x + 2*barpad + max([barsize_px,textsize[0]]))/2 - textsize[0]/2
        texty = y + textpad
        
        #color for bar and text
        if invert:
            color = 255
        else:
            color = 0
        
        #draw scalebar
        exportim = cv2.rectangle(
            exportim,
            (int(barx),int(bary)),
            (int(barx+barsize_px),int(bary+barheight)),
            color,
            -1
        )
        
        #draw text
        exportim = Image.fromarray(exportim)
        draw = ImageDraw.Draw(exportim)
        draw.text(
            (textx,texty),
            text,
            fill=color,
            font=font
        )
        exportim = np.array(exportim)
        
        #show result
        plt.figure()
        plt.imshow(exportim,cmap='gray',vmin=0,vmax=255)
        plt.title('exported image')
        plt.axis('off')
        plt.tight_layout()
        
        #save image
        cv2.imwrite(filename,exportim)