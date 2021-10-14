import numpy as np
import os
from PIL import Image
from warnings import warn

class tecnai:
    """
    Set of convenience functions for electron microscopy images of the tecnai
    12, 20, 20feg and Talos microscopes. Initializing the class takes a string
    containing the filename as only argument, and by default loads in the
    image.
    
    Parameters
    ----------
    filename : string
        name of the file to load. Can but is not required to include .tif
        as extension.
    """
    
    def __init__(self,filename):
        #raise error if wrong format or file does not exist
        if type(filename) != str:
            raise TypeError('The argument to the '+self.__name__+
                            ' class must be a string containing the filename.')
        if not os.path.exists(filename):
            if os.path.exists(filename + '.tif'):
                filename = filename + '.tif'
            else:
                raise FileNotFoundError('The file "'+filename+'" could not be found.')
        
        self.filename = filename
        
        #load the image
        self.PIL_image = Image.open(filename)
        im = np.array(self.PIL_image)
        self.shape = np.shape(im)
        self.image = im[:self.shape[1]]
        self.scalebar = im[self.shape[1]:]
        self.dtype = self.image.dtype
    
    def get_metadata(self,asdict=False):
        """
        loads xml metadata from .tif file and returns xml tree object or dict

        Parameters
        ----------
        asdict : bool, optional
            whether to export as a dictionary. When False, an 
            `xml.etree.ElementTree` is returned. The default is False.

        Returns
        -------
        dictionary or xml root object
            dictionary or xml root object of the metadata. Can be indexed with
            xml_root.find('<element name>')

        """
        #try to get metadata tag, raise warning if not found
        try:
            metadata = self.PIL_image.tag[34682][0]
        except KeyError:
            warn('no metadata found')
            return None
        
        if asdict:
            import re
            
            #convert to dictionary
            metadatadict = {}
            for item in re.findall(r'<Data>(.*?)</Data>',metadata):
                label = re.findall(r'<Label>(.*?)</Label>',item)[0]
                unit = re.findall(r'<Unit>(.*?)</Unit>',item)[0]
                value = re.findall(r'<Value>(.*?)</Value>',item)[0]
                
                metadatadict[label] = {"value":value,"unit":unit}
            
            #add pixelsize if already known for this class instance
            try:
                value = self.pixelsize
                unit = self.unit
                metadatadict['Pixel size'] = {'value':value,'unit':unit}
            except AttributeError:
                pass
            
            self.metadata = metadatadict
            
        else:
            import xml.etree.ElementTree as et
            self.metadata = et.fromstring(metadata)
        
        return self.metadata
    
    
    def print_metadata(self):
        """prints formatted output of the file's metadata"""
        metadata = self.get_metadata(asdict=True)
        
        #don't print anything when metadata is empty
        if metadata is None or len(metadata) == 0:
            return
        
        #get max depth
        l = max(len(i) for i in metadata)
        
        #print header, contents and footer
        print('\n-----------------------------------------------------')
        print('METADATA')
        print(self.filename)
        print('-----------------------------------------------------')
        for i,k in metadata.items():
            string = i+':\t'+str(k['value'])+' '+str(k['unit'])
            print(string.expandtabs(l+2))
        print('-----------------------------------------------------\n')
            
    
    def get_pixelsize(self,convert=None):
        """
        Gets the physical size represented by the pixels from the image 
        metadata
        
        Parameters
        ----------
        convert : one of ['m', 'mm', 'um', 'µm', 'nm', 'pm', None], optional
            physical unit to use for the pixel size. The default is None, which
            chooses one of the above automatically based on the value.
        
        Returns
        -------
        pixelsize : float
            the physical size of a pixel in the given unit
        unit : str
            physical unit of the pixel size
        """
        #tiff tags 65450 and 65451 contain an int value for pixels per `n` cm,
        #where n is a power of 10, e.g. 586350674 pixels per 100 cm is 
        #encoded as (586350674, 100) and gives 1.7 nm/pixel
        try:
            pixelsize_x = self.PIL_image.tag[65450][0]
        except KeyError:
            #old tecnai 12 has it in key 282 and 283 instead
            try:
                pixelsize_x = self.PIL_image.tag[282][0]
            except KeyError:
                raise KeyError('pixel size not found in file data')
        
        pixelsize_x = 1e-2*pixelsize_x[1]/pixelsize_x[0]
        
        #pixelsize_y = self.PIL_image.tag[65451][0]
        #pixelsize_y = 1e-2*pixelsize_y[1]/pixelsize_y[0]
        
        #find the right unit and rescale for convenience
        if convert is None:
            if pixelsize_x >= 10e-3:
                unit = 'm'
            elif pixelsize_x < 10e-3 and pixelsize_x >= 10e-6:
                unit = 'mm'
                pixelsize_x = 1e3*pixelsize_x
                #pixelsize_y = 1e3*pixelsize_y
            elif pixelsize_x < 10e-6 and pixelsize_x >= 10e-9:
                unit = 'µm'
                pixelsize_x = 1e6*pixelsize_x
                #pixelsize_y = 1e6*pixelsize_y
            elif pixelsize_x < 10e-9 and pixelsize_x >= 10e-12:
                unit = 'nm'
                pixelsize_x = 1e9*pixelsize_x
                #pixelsize_y = 1e9*pixelsize_y
            else:
                unit = 'pm'
                pixelsize_x = 1e12*pixelsize_x
                #pixelsize_y = 1e9*pixelsize_y
        #else use given unit
        else:
            #allow um for convenience
            if convert == 'um':
                convert = 'µm'
            
            #check against list of allowed units
            unit = 'm'
            units = ['pm','nm','µm','mm','m']
            if not convert in units:
                raise ValueError('"'+str(convert)+'" is not a valid unit')
            
            #factor 10**3 for every step from list, use indices to calculate
            pixelsize_x = pixelsize_x*10**(
                3*(units.index(unit)-units.index(convert))
            )
            unit = convert
            
        #store and return
        self.pixelsize = pixelsize_x
        self.unit = unit
        return (pixelsize_x,unit)
    
    def get_pixelsize_legacy(self, debug=False):
        """
        .. deprecated::
           This function has been deprecated and may give slightly inaccurate 
           result (only accurate to the nearest whole pixel), use 
           `tecnai.get_pixelsize()` for more accurate and faster calibration. 
           Included for cases where results using the previous calibration 
           method must be reproduced or compared with.
        
        Reads the scalebar from images of the Tecnai TEM microscopes using 
        text recognition via pytesseract or with manual input when pytesseract
        is not installed

        Parameters
        ----------
        debug : bool, optional
            enable debug mode which prints extra information and figures to
            troubleshoot any issues with calibration. The default is False.

        Returns
        -------
        pixelsize : float
            the pixelsize in calibrated (physical) units
        unit : string
            the physical unit of the pixelsize

        """
        import re
        import cv2
        
        #find contour corners sorted left to right
        if len(self.scalebar) == 0:
            print('[WARNING] tecnai.get_pixelsize: original scale bar not found!')
            pixelsize = float(input('Please give pixelsize in nm: '))
            self.unit = 'nm'
            self.pixelsize = pixelsize
            return pixelsize,'nm'
        else:
            sb = self.scalebar
            if self.dtype != np.uint8:
                sb = ((sb-sb.min())/((sb.max()-sb.min())/255)).astype(np.uint8)
            if int(cv2.__version__[0]) >= 4:
                corners,_ = cv2.findContours(sb,cv2.RETR_LIST,cv2.CHAIN_APPROX_SIMPLE)
            else:
                _,corners,_ = cv2.findContours(sb,cv2.RETR_LIST,cv2.CHAIN_APPROX_SIMPLE)
            corners = sorted(corners, key=lambda c: cv2.boundingRect(c)[0])
        
        #length in pixels between bottom left corners of vertical bars
        barlength = corners[0][7,0,0]-corners[0][1,0,0]
        
        if debug:
            import matplotlib.pyplot as plt
            print('\n------- DEBUGGING IMAGE CALIBRATION -------')
            print('- length:',barlength,'pixels')
            plt.figure('[DEBUG MODE] scale bar corners')
            plt.imshow(self.scalebar)
            plt.scatter(corners[0][:,0,0],corners[0][:,0,1],color='r',label='corners')
            plt.scatter(corners[0][[1,7],0,0],corners[0][[1,7],0,1],color='green',label='used for calibration')
            plt.legend()
            plt.show(block=False)
        
        #take the text of the databar
        bartext = self.scalebar[:,
            min(corners[1][:,0,0])-int(6*self.shape[1]/1024):\
                max(corners[-1][:,0,0])+int(6*self.shape[1]/1024+1)
        ]
        bartext = bartext.max() - bartext
        
        #upscale if needed for OCR
        if self.shape[1] < 4096:
            if self.shape[1] < 2048:
                factor = 4
            else:
                factor = 2
            bartextshape = np.shape(bartext)
            bartext = cv2.resize(
                bartext,
                (factor*bartextshape[1],factor*bartextshape[0]),
                interpolation = cv2.INTER_CUBIC
            )
            bartext = cv2.erode(
                cv2.threshold(bartext,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)[1],
                np.ones((5,5),np.uint8)
            )
            if debug:
                print('- preprocessing text, resizing text image from',bartextshape,'to',np.shape(bartext))
        
        try:
            #load tesseract-OCR for reading the text
            import pytesseract
            
            #switch error handling from a ValueError (we may also raise later
            #in case of text recognition problems) to one we can only raise 
            #here, so we can give the correct warning
            try:
                tesseract_version = float(str(pytesseract.get_tesseract_version())[:3])
            except ValueError:
                raise FileNotFoundError
            
            #settings vary per version, so use tesseract_verion to use correct
            if tesseract_version == 4.0:
                text = pytesseract.image_to_string(
                    bartext,
                    config="--oem 0 -c tessedit_char_whitelist=0123456789pnuµm --psm 7"
                )
                #oem 0 selects older version of tesseract which still takes the char_whitelist param
                #tessedit_char_whitelist takes list of characters it searches for (to reduce reading errors)
                #psm 7 is a mode that tells tesseract to assume a single line of text in the image
            else:
                text = pytesseract.image_to_string(
                    bartext,
                    config="-c tessedit_char_whitelist=0123456789pnuµm --psm 7"
                )
                #since version 4.1 char whitelist is added back
            
            text = text.replace('\x0c','')
            if debug:
                plt.figure('[DEBUG MODE] scale bar text')
                plt.imshow(bartext)
                plt.show(block=False)
                print('- text:',text)
                
            #split value and unit
            value = float(re.findall(r'\d+',text)[0])
            unit = re.findall(r'[a-z]+',text)[0]
        
        #give different warnings for missing installation or reading problems
        except ImportError:
            print('pytesseract not found, defaulting to manual mode')
            unit = input('give scale bar unit: ')
            value = float(input('give scale bar size in '+unit+': '))
        except FileNotFoundError:
            print('[WARNING] tecnai.get_pixelsize(): tesseract OCR engine was'+
                  ' not found by pytesseract. Switching to manual mode.')
            unit = input('give scale bar unit: ')
            value = float(input('give scale bar size in '+unit+': '))
        except:
            print('[WARNING] tecnai.get_pixelsize(): could not read scale bar'+
                  ' text, perhaps try debug=True. Switching to manual mode.')
            unit = input('give scale bar unit: ')
            value = float(input('give scale bar size in '+unit+': '))
        
        if unit == 'um':
            unit = 'µm'
        
        #determine pixelsize
        pixelsize = value/barlength
        
        if debug:            
            print('- value:',value)
            print('- unit:',unit)
            print('- 2 figures created')
            print('-------------------------------------------\n')
        
        print('Original scale bar: {:.3g}'.format(value),unit)
        print('Pixel size: {:.5g}'.format(pixelsize),unit)
        
        self.pixelsize = pixelsize
        self.unit = unit

        
        return pixelsize,unit
        
    def export_with_scalebar(self, filename=None, **kwargs):
        """
        saves an exported image of the TEM image with a scalebar in one of the 
        four corners, where barsize is the scalebar size in data units (e.g. 
        nm) and scale the overall size of the scalebar and text with respect to
        the width of the image.

        Parameters
        ----------
        filename : string or `None`, optional
            Filename + extension to use for the export file. The default is the
            filename sans extension of the original TEM file, with 
            '_exported.png' appended.
        crop : tuple or `None`, optional 
            range describing a area of the original image (before rescaling the
            resolution) to crop out for the export image. Can have two forms:
                
            - `((xmin,ymin),(xmax,ymax))`, with the integer indices of the top
            left and bottom right corners respectively.
                
            - `(xmin,ymin,w,h)` with the integer indices of the top left corner
            and the width and heigth of the cropped image in pixels (prior to 
            optional rescaling using `resolution`).
            
            The default is `None` which takes the entire image.
        resolution : int, optional
            the resolution along the x-axis (i.e. image width in pixels) to use
            for the exported image. The default is `None`, which uses the size 
            of the original image (after optional cropping using `crop`).
        draw_bar : boolean, optional
            whether to draw a scalebar on the image, such that this function 
            may be used just to strip the original bar and crop. The default is
            `True`.
        barsize : float or `None`, optional
            size (in data units matching the original scale bar, e.g. nm) of 
            the scale bar to use. The default `None`, wich takes the desired 
            length for the current scale and round this to the nearest option
            from a list of "nice" values.
        scale : float, optional
            factor to change the size of the scalebar+text with respect to the
            width of the image. Scale is chosen such, that at `scale=1` the
            font size of the scale bar text is approximately 10 pt when 
            the image is printed at half the width of the text in a typical A4
            paper document (e.g. two images side-by-side). The default is 1.
        loc : int, one of [`0`,`1`,`2`,`3`], optional
            Location of the scalebar on the image, where `0`, `1`, `2` and `3` 
            refer to the top left, top right, bottom left and bottom right 
            respectively. The default is `2`, which is the bottom left corner.
        convert : one of ['pm', 'nm', 'um', 'µm', 'mm', 'm', None], optional
            Unit that will be used for the scale bar, the value will be 
            automatically converted if this unit differs from the pixel size
            unit. The default is `None`, which uses the unit of the scalebar on
            the original image.
        font : str, optional
            filename of an installed TrueType font ('.ttf' file) to use for the
            text on the scalebar. The default is `'arialbd.ttf'`.
        fontsize : int, optional
            base font size to use for the scale bar text. The default is 16. 
            Note that this size will be re-scaled according to `resolution` and
            `scale`.
        fontbaseline : int, optional
            vertical offset for the baseline of the scale bar text in printer
             points. The default is 0.
        fontpad : int, optional
            minimum size in printer points of the space/padding between the 
            text and the bar and surrounding box. The default is 2.
        barthickness : int, optional
            thickness in printer points of the scale bar itself. The default is
            16.
        barpad : int, optional
            size in printer points of the padding between the scale bar and the
            surrounding box. The default is 10.
        box : bool, optional
            Whether to put a semitransparent box around the scalebar and text
            to enhance contrast. The default is `True`.
        boxalpha : float, optional
            value between 0 and 1 for the opacity (inverse of transparency) of
            the box behind the scalebar and text when `box=True`. The default 
            is `0.6`.
        invert : bool, optional
            If `True`, a white scalebar and text on a black box are used. The 
            default is `False` which gives black text on a white background.
        boxpad : int, optional
            size of the space/padding around the box (with respect to the sides
            of the image) in printer points. The default is 10.
        """
        #check if pixelsize already calculated, otherwise call get_pixelsize
        try:
            pixelsize,unit = self.pixelsize,self.unit
        except AttributeError:
            pixelsize,unit = self.get_pixelsize()
        
        #set default export filename
        if type(filename) != str:
            filename = self.filename.rpartition('.')[0]+'_scalebar.png'
        
        #check we're not overwriting the original file
        if filename==self.filename:
            raise ValueError('overwriting original TEM file not reccomended, '+
                             'use a different filename for exporting.')
        
        #get image
        exportim = self.image.copy()
        
        #call main export_with_scalebar function with correct pixelsize etc
        from .utility import _export_with_scalebar
        _export_with_scalebar(exportim, pixelsize, unit, filename, **kwargs)