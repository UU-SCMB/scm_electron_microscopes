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
            if int(cv2.__version__[0]) >= 4:
                corners,_ = cv2.findContours(self.scalebar,cv2.RETR_LIST,cv2.CHAIN_APPROX_SIMPLE)
            else:
                _,corners,_ = cv2.findContours(self.scalebar,cv2.RETR_LIST,cv2.CHAIN_APPROX_SIMPLE)
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
            
            #settings vary per version
            tesseract_version = float(str(pytesseract.get_tesseract_version())[:3])
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
    
    def export_with_scalebar(self,filename=None,barsize=None,crop=None,scale=1,
                             loc=2,resolution=None,box=True,invert=False,
                             convert=None):
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
            the scale bar to use. The default 15% of the image width rounded to
            the nearest 'nice' value.
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
            raise ValueError('overwriting original TEM file not reccomended, '+
                             'use a different filename for exporting.')
        
        #get image
        exportim = self.image.copy()
        
        #call main export_with_scalebar function with correct pixelsize etc
        from .utility import _export_with_scalebar
        _export_with_scalebar(exportim, pixelsize, unit, filename, barsize, 
                              crop, scale, loc, resolution, box, invert, 
                              convert)