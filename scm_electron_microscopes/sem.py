
#==============================================================================
# HELIOS
#==============================================================================
import os
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
