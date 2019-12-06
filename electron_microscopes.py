# -*- coding: utf-8 -*-
"""
created by:     Maarten Bransen
email:          m.bransen@uu.nl
last updated:   05-11-2019
"""

import cv2
import numpy as np


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


        Returns
        -------
        None.

        """

        #raise error if wrong format or file does not exist
        if type(filename) != str:
            raise TypeError('The argument to the tecnai class must be a string containing the filename.')
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
        bartext = self.scalebar[:,min(corners[1][:,0,0])-int(6*self.shape[1]/1024):max(corners[-1][:,0,0])+int(6*self.shape[1]/1024+1)]
        
        #upscale if needed for OCR
        if self.shape[1] < 4096:
            if self.shape[1] < 2048:
                factor = 4
            else:
                factor = 2
            bartextshape = np.shape(bartext)
            bartext = cv2.resize(bartext,(factor*bartextshape[1],factor*bartextshape[0]),interpolation = cv2.INTER_CUBIC)
            bartext = cv2.erode(cv2.threshold(bartext,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)[1],np.ones((5,5),np.uint8))
            if debug:
                print('- preprocessing text, resizing text image from',bartextshape,'to',np.shape(bartext))
        
        try:
            #read the text
            import pytesseract
            text = pytesseract.image_to_string(bartext,config="--oem 0 -c tessedit_char_whitelist=0123456789pnuµm --psm 7")
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

#==============================================================================
# HELIOS
#==============================================================================
import os
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
        """
        Load the metadata footer from Helios SEM files and return xml tree
        object which can be indexed for extraction of useful parameters. Does
        not require loading whole file into memory. Attempts first to find xml
        formatted data, if this is not found it looks for 'human' formatted
        metadata.
        
        @dependencies:
            import io
            import xml.etree.ElementTree as et
        
        @parameters:
            self.filename:   string
        
        @returns:
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
        """gets the pixel size from the metadata and calculates the unit"""
        
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
        pixelsize = (pixelsize_x,pixelsize_y)
        print('Pixel size x: {:.6g}'.format(pixelsize[0]),unit)
        print('Pixel size y: {:.6g}'.format(pixelsize[1]),unit)
        
        self.pixelsize= pixelsize
        self.unit = unit
        
        return pixelsize,unit


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
        """
        Load the metadata footer from XL30SFEG SEM files and return xml tree object
        which can be indexed for extraction of useful parameters. Does not require
        loading whole file into memory. Searches for 'human' formatted metadata.
        
        @dependencies:
            import io
            import xml.etree.ElementTree as et
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
        """gets the pixelsize from the data"""
        #try finding metadata, else call load_metadata
        try:
            self.metadata
        except AttributeError:
            self.load_metadata()
        
        
        self.pixelsize = float(self.metadata.find('DatabarData').find('flMagn').text)
        self.unit = 'µm'
        
        return self.pixelsize,self.unit


class util:
    """utility functions"""
    
    def _printchild(element,prefix):
        """
        recursive function for printing xml metadata with subelements
        """
        #if there are subelements, print and call itself on subelements
        if element:
            if element.attrib:
                print(prefix + element.tag + ' ' + str(element.attrib) + ':')
            else:
                print(prefix + element.tag + ':')
            for child in element:
                util._printchild(child,prefix=prefix+'   ')
        
        #otherwise, just print available info
        else:
            if not element.attrib:#if attributes are empty
                print(prefix + element.tag + ' = ' + element.text)
            elif 'unit' in element.attrib:#if not, get unit from attributes
                print(prefix + element.tag + ' = ' + element.text + ' ' + element.attrib['unit'])
            elif element.text:#when attributes not empty check if there is text
                print(prefix + element.tag + ' = ' + str(element.attrib) + element.text)
            else:
                print(prefix + element.tag + ' = ' + str(element.attrib))
    
    def print_metadata(xml_root):
        """
        print xml attributes/tags of phenom data to inspect elements.
        
        @dependencies:
            import xml.etree.ElementTree as et
        
        @parameters:
            xml_root: output of get_metadata()
        
        @returns:
            none, but prints output
        """       
        print('-----------------------------------------------------')
        print('METADATA')
        print('-----------------------------------------------------')
        
        for element in xml_root:
            util._printchild(element,prefix='')
        
        print('-----------------------------------------------------\n')
        
    def image_histogram(image,binsize=1,log=True):
        """plot histogram of the image grey values"""
        
        import matplotlib.pyplot as plt
        minval = np.iinfo(image.dtype).min
        maxval = np.iinfo(image.dtype).max
        
        bins = np.linspace(minval,maxval,int((maxval-minval)/binsize))
        
        plt.figure()
        plt.hist(np.ravel(image),bins=bins,log=log)
        plt.xlabel('grey value')
        plt.ylabel('occurrence')




















