import cv2
import numpy as np
import os

class tecnai:
    """
    Set of convenience functions for electron microscopy images of the tecnai
    12, 20, 20feg and Talos microscopes. Initializing the class takes a string
    containing the filename as only argument, and by default loads in the
    image.
    """
    
    def __init__(self,filename):
        """
        initialize class by loading the file

        Parameters
        ----------
        filename : string
            name of the file to load. Can but is not required to include .tif
            as extension.
        """

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
        im = cv2.imread(filename,0)
        self.shape = np.shape(im)
        self.image = im[:self.shape[1]]
        self.scalebar = im[self.shape[1]:]
    
    def load_metadata(self,asdict=True):
        """
        loads xml metadata from .tif file and returns xml tree object

        Parameters
        ----------
        asdict : bool, optional
            whether to export as dictionary. The default is True.

        Returns
        -------
        dictionary or xml root object
            dictionary or xml root object of the metadata. Can be indexed with
            xml_root.find('<element name>')

        """
        import io
        import re

        metadata = ''
        read = False
        
        with io.open(self.filename, 'r', errors='ignore', encoding='utf8') as f:
            #iterate through file line by line to avoid loading too much into memory
            for line in f:
                #start reading at the first line containing an xml tag
                if '<Root' in line:
                    read = True
                if read:
                    metadata += line
                    if '</Root' in line:
                        break #stop at line with end tag
            
        #trim strings down to only xml
        metadata = metadata[metadata.find('<Root'):]
        metadata = metadata[:metadata.find('</Root')+7]
        
        if asdict:
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
                sblen = self.scalebarlength
                metadatadict['Pixel size'] = {'value':value,'unit':unit}
                metadatadict['Scale bar size'] = {'value':sblen,'unit':unit}
            except AttributeError:
                pass
            
            self.metadata = metadatadict
            
        else:
            import xml.etree.ElementTree as et
            self.metadata = et.fromstring(metadata)
        
        return self.metadata
    
    
    def print_metadata(self):
        """prints formatted output of the file's metadata"""
        
        metadata = self.load_metadata()
        
        l = max(len(i) for i in metadata)
        
        print('\n-----------------------------------------------------')
        print('METADATA')
        print('-----------------------------------------------------')
        
        for i,k in metadata.items():
            string = i+':\t'+str(k['value'])+' '+str(k['unit'])
            print(string.expandtabs(l+2))
        
        print('-----------------------------------------------------\n')
            
    
    def get_pixelsize(self, debug=False):
        """
        Reads the scalebar from images of the Tecnai TEM microscopes using 
        text recognition via pytesseract or with manual imput when pytesseract
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
        
        #find contour corners sorted left to right
        if len(self.scalebar) == 0:
            print('[WARNING] tecnai.get_pixelsize: original scale bar not found!')
            pixelsize = float(input('Please give pixelsize in nm: '))
            self.unit = 'nm'
            self.pixelsize = pixelsize
            return pixelsize,'nm'
        else:
            corners,_ = cv2.findContours(self.scalebar,cv2.RETR_LIST,cv2.CHAIN_APPROX_SIMPLE)
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
        
        #take the text of the databar
        bartext = self.scalebar[:,
            min(corners[1][:,0,0])-int(6*self.shape[1]/1024):\
                max(corners[-1][:,0,0])+int(6*self.shape[1]/1024+1)
        ]
        
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
            #read the text
            import pytesseract
            text = pytesseract.image_to_string(
                bartext,
                config="--oem 0 -c tessedit_char_whitelist=0123456789pnuµm --psm 7"
            )
            #oem 0 selects older version of tesseract which still takes the char_whitelist param
            #tessedit_char_whitelist takes list of characters it searches for (to reduce reading errors)
            #psm 7 is a mode that tells tesseract to assume a single line of text in the image

            if debug:
                plt.figure('[DEBUG MODE] scale bar text')
                plt.imshow(bartext)
                print('- text:',text)
                
            #split value and unit
            value = float(re.findall(r'\d+',text)[0])
            unit = re.findall(r'[a-z]+',text)[0]
            
        except:
            print('[WARNING] tecnai.get_pixelsize(): could not read scale bar text')
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
        self.scalebarlength = value
        self.scalebarlength_px = barlength
        
        return pixelsize,unit
    
    def export_with_scalebar(self,filename,barsize=None,scale=1,loc=0,
                             resolution=None,box=True,invert=False):
        
        #check if pixelsize already calculated, otherwise call get_pixelsize
        try:
            pixelsize,unit = self.pixelsize,self.unit
        except AttributeError:
            pixelsize,unit = self.get_pixelsize()
        
        #set default scalebar to original scalebar or calculate len
        if type(barsize) == type(None):
            barsize_px = self.scalebarlength_px
        else:
            barsize_px = barsize/pixelsize
        
        #set default resolution or correct barlen_px
        if type(resolution) == type(None):
            resolution = self.shape[1]
        else:
            barsize_px = barsize_px/self.shape[1]*resolution
        
        #TODO resolution correction
        scale = scale*resolution/1024
        exportim = self.image.copy()
        
        boxheight = int(scale*80)
        barheight = int(scale*20)
        
        #bottom left
        if loc == 0:
            x = int(10*scale)
            y = int(resolution - 10*scale - boxheight)
        #bottom right
        elif loc == 1:
            x = int(resolution - 30*scale - barsize_px)
            y = int(resolution - 10*scale - boxheight)
        #top left
        elif loc == 2:
            x = int(10*scale)
            y = int(10*scale)
        #top right
        elif loc == 3:
            x = int(resolution - 30*scale - barsize_px)
            y = int(10*scale)
        else:
            raise ValueError("loc must be 0, 1, 2 or 3")
        
        #put semitransparent box
        if box:
            #get rectangle from im and create box
            w,h = int(20*scale+barsize_px),int(boxheight)
            subim = exportim[y:y+h, x:x+w]
            white_box = np.ones(subim.shape, dtype=np.uint8) * 255
            
            #add or subtract box from im, and put back in im
            if invert:
                exportim[y:y+h, x:x+w] = cv2.addWeighted(subim, 0.5, -white_box, 0.5, 1.0)
            else:
                exportim[y:y+h, x:x+w] = cv2.addWeighted(subim, 0.5, white_box, 0.5, 1.0)

        #put scalebar itself and text on im
        barx = int(x+10*scale)
        bary = int(y+boxheight-10*scale-barheight)
        
        text = str(barsize)+' '+unit,(textx,texty)
        font = cv2.FONT_HERSHEY_DUPLEX
        textx = int((2*barx + barsize_px)//2-cv2.getTextSize(text, font, 1, 2)[0])
        texty = int(bary - 10*scale)
        
        if invert:
            exportim = cv2.rectangle(exportim,(barx,y),(barx+barsize_px,bary+barheight),255,-1)
            exportim = cv2.putText(exportim,,font,scale*1,255,-1)
        else:
            exportim = cv2.rectangle(exportim,(barx,bary),(int(barx+barsize_px),bary+barheight),0,-1)
            exportim = cv2.putText(exportim,str(barsize)+' '+unit,(textx,texty),font,scale*1,0,1)
        
        