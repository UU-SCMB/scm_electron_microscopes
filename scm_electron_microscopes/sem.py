import os
import numpy as np
from .utility import util
from PIL import Image
from warnings import warn

class helios:
    """
    Set of convenience functions for the Helios SEM.
    
    Parameters
    ----------
    filename : string
        name of the file to load. Can but is not required to include .tif
        as extension.


    Returns
    -------
    helios class instance
    """
    def __init__(self,filename):
        #raise error if wrong format or file does not exist
        if type(filename) != str:
            raise TypeError('The argument to the helios class must be a string'
                            ' containing the filename.')
        if not os.path.exists(filename):
            if os.path.exists(filename + '.tif'):
                filename = filename + '.tif'
            else:
                raise FileNotFoundError('The file "'+filename+
                                        '" could not be found.')
        self.filename = filename
        self.PIL_image = Image.open(self.filename)
        self.shape = self.PIL_image.size[::-1]
    
    def get_image(self):
        """
        load the image and split into image and databar

        Returns
        -------
        numpy.array
            array of pixel values in the image (not including the data bar)

        """
        im = np.array(self.PIL_image)
        self.image = im[:int(self.shape[1]/1.5)]
        if int(self.shape[1]/1.5) < self.shape[0]:
            self.databar = im[int(self.shape[1]/1.5):]
        else:
            self.databar = None
        return self.image
    
    def get_metadata(self):
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
            `xml_root.find('<element name>')`.

        """
        import xml.etree.ElementTree as et
        
        #two possible formats, 'standard' and images from slice and view series
        #try first to get xml from slice and view
        try:
            xml_root = et.fromstring(self.PIL_image.tag[34683][0])
        except KeyError:
            xml_root = et.Element('MetaData')
        
        try:
            #get value from tiff tag 34682 which contains the metadata in a 
            #human readable format
            metadata = self.PIL_image.tag[34682][0].split('\r\n')
            
            #check for empty metadata, raise keyerror for exception catching
            if len(metadata) == 0:
                raise KeyError
            
            #construct/add to xml object
            for line in metadata:
                if line:#if not empty line
                    if line[0] == '[':
                        child = et.SubElement(xml_root,line[1:-1])
                    else:
                        line = line.split('=')
                        subchild = et.SubElement(child,line[0])
                        subchild.text = line[1]
            
            #store and return xml root
            self.metadata = xml_root
            return xml_root
        
        #if the metadata key is not found in the image
        except KeyError:
            warn('no metadata found')
            return None
    
    def print_metadata(self):
        """print formatted output of metadata"""
        
        try:
            xml_root = self.metadata
        except AttributeError:
            xml_root = self.get_metadata()
        
        util.print_metadata(xml_root)
        
        
    def get_pixelsize(self):
        """
        gets the pixel size from the metadata and calculates the unit

        Returns
        -------
        pixelsize : tuple of float
            the pixelsize in calibrated (physical) units in (x,y)
        unit : string
            the physical unit of the pixel size

        """
        #get the metadata or load it if it is not (yet) available
        try:
            xml_root = self.metadata
        except AttributeError:
            xml_root = self.get_metadata()
        
        #find the pixelsize (may be two different formats)
        try:
            pixelsize_x = float(xml_root.find('Scan').find('PixelWidth').text)
            pixelsize_y = float(xml_root.find('Scan').find('PixelHeight').text)
        except:
            pixelsize_x = float(
                xml_root.find('BinaryResult').find('PixelSize').find('X').text
            )
            pixelsize_y = float(
                xml_root.find('BinaryResult').find('PixelSize').find('Y').text
            )
        
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
        
        #print pixel size
        #print('Pixel size x: {:.6g}'.format(pixelsize[0]),unit)
        #print('Pixel size y: {:.6g}'.format(pixelsize[1]),unit)
        
        self.pixelsize = pixelsize
        self.unit = unit
        
        return pixelsize,unit
    
    def export_with_scalebar(self, filename=None, **kwargs):
        """
        saves an exported image of the SEM image with a scalebar in one of the 
        four corners, where barsize is the scalebar size in data units (e.g. 
        nm) and scale the overall size of the scalebar and text with respect to
        the width of the image.

        Parameters
        ----------
        filename : string or `None`, optional
            Filename + extension to use for the export file. The default is the
            filename sans extension of the original SEM file, with 
            '_exported.png' appended.
        preprocess : callable, optional
            callable to pre-process the image before any other processing is 
            done, useful for e.g. smoothing. Must take and return a 
            numpy.ndarray containing the image data as only arguments, and must
            not change e.g. the pixel size or the scale bar may be incorrectly 
            sized. The default is None.
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
            is `0.8`.
        invert : bool, optional
            If `True`, a white scalebar and text on a black box are used. The 
            default is `False` which gives black text on a white background.
        boxpad : int, optional
            size of the space/padding around the box (with respect to the sides
            of the image) in printer points. The default is 10.
        store_settings : bool, optional
            when `True`, a .txt file is saved along with the image containing
            all settings passed to this function. The default is False
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
            raise ValueError('overwriting original SEM file not recommended, '+
                             'use a different filename for exporting.')
              
        #get and display image
        try:
            exportim = self.image.copy()
        except AttributeError:
            exportim = self.get_image().copy()
        
        #call main export_with_scalebar function with correct pixelsize etc
        from .utility import _export_with_scalebar
        _export_with_scalebar(exportim, pixelsize[0], unit, filename, **kwargs)


#==============================================================================
# PHENOM
#==============================================================================
class phenom:
    """
    Set of convenience functions for the phenom SEM microscopes.
    
    Parameters
    ----------
    filename : str
        filename of the image to load
        
    Returns
    -------
    phenom class instance
    """
    def __init__(self,filename):
        #raise error if wrong format or file does not exist
        if type(filename) != str:
            raise TypeError('The argument to the helios class must be a string'
                            ' containing the filename.')
        if not os.path.exists(filename):
            raise FileNotFoundError('The file "'+filename+
                                    '" could not be found.')
            
        self.filename = filename
        self.PIL_image = Image.open(filename)
        self.shape = self.PIL_image.size[::-1]
    
    def get_image(self):
        """load the image and split into image and databar"""
        im = np.array(self.PIL_image)
        self.image = im[:int(self.shape[1])]
        self.databar = im[int(self.shape[1]):]
        return self.image
    
    def get_metadata(self):
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
            xml_root = self.get_metadata()
        
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
            xml_root = self.get_metadata()
        
        #find the pixelsize (may be two different formats)
        pixelsize_x = float(xml_root.find('pixelWidth').text)
        pixelsize_y = float(xml_root.find('pixelHeight').text)
        
        #get the unit
        if xml_root.find('pixelWidth').attrib['unit'] != \
            xml_root.find('pixelHeight').attrib['unit']:
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

    def export_with_scalebar(self, filename=None, **kwargs):
        """
        saves an exported image of the SEM image with a scalebar in one of the 
        four corners, where barsize is the scalebar size in data units (e.g. 
        nm) and scale the overall size of the scalebar and text with respect to
        the width of the image.

        Parameters
        ----------
        filename : string or `None`, optional
            Filename + extension to use for the export file. The default is the
            filename sans extension of the original SEM file, with 
            '_exported.png' appended.
        preprocess : callable, optional
            callable to pre-process the image before any other processing is 
            done, useful for e.g. smoothing. Must take and return a 
            numpy.ndarray containing the image data as only arguments, and must
            not change e.g. the pixel size or the scale bar may be incorrectly 
            sized. The default is None.
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
            is `0.8`.
        invert : bool, optional
            If `True`, a white scalebar and text on a black box are used. The 
            default is `False` which gives black text on a white background.
        boxpad : int, optional
            size of the space/padding around the box (with respect to the sides
            of the image) in printer points. The default is 10.
        store_settings : bool, optional
            when `True`, a .txt file is saved along with the image containing
            all settings passed to this function. The default is False
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
            raise ValueError('overwriting original SEM file not recommended, '+
                             'use a different filename for exporting.')
              
        #get and display image
        try:
            exportim = self.image.copy()
        except AttributeError:
            exportim = self.get_image().copy()
        
        #call main export_with_scalebar function with correct pixelsize etc
        from .utility import _export_with_scalebar
        _export_with_scalebar(exportim, pixelsize[0], unit, filename, **kwargs)


class xl30sfeg:
    """
    Set of convenience functions for the xl30sfeg SEM microscope.
    
    Parameters
    ----------
    filename : str
        filename of the image to load
        
    Returns
    -------
    xl30sfeg class instance
    """
    def __init__(self,filename):
        #raise error if wrong format or file does not exist
        if type(filename) != str:
            raise TypeError('The argument to the xl30sfeg class must be a '
                            'string containing the filename.')
        if not os.path.exists(filename):
            raise FileNotFoundError('The file "'+filename+
                                    '" could not be found.')
        
        self.filename = filename
        self.PIL_image = Image.open(filename)
        self.shape = self.PIL_image.size[::-1]
    
    def get_image(self):
        """load the image and (if present) scalebar"""
        
        im = np.array(self.PIL_image)
        self.image = im[:int(self.shape[1]/1.330)]
        
        #check if scalebar is present
        if len(im) > int(self.shape[1]/1.330):
            self.scalebar = im[int(self.shape[1]/1.330):]
        
        return self.image
    
    
    def get_metadata(self):
        """Load the metadata footer from XL30SFEG SEM files and return xml 
        tree object which can be indexed for extraction of useful parameters. 
        Does not require loading whole file into memory. Searches for 'human' 
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
        with io.open(self.filename, 'r', errors='ignore', encoding='utf8') \
            as file:
            for line in file:
                #start reading at first line with [DatabarData], break at last 
                #item
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
            xml_root = self.get_metadata()
        
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
        #try finding metadata, else call get_metadata
        try:
            self.metadata
        except AttributeError:
            self.get_metadata()
        
        self.pixelsize = float(
            self.metadata.find('DatabarData').find('flMagn').text
        )
        self.unit = 'µm'
        
        return self.pixelsize,self.unit

    def export_with_scalebar(self, filename=None, **kwargs):
        """
        saves an exported image of the SEM image with a scalebar in one of the 
        four corners, where barsize is the scalebar size in data units (e.g. 
        nm) and scale the overall size of the scalebar and text with respect to
        the width of the image.

        Parameters
        ----------
        filename : string or `None`, optional
            Filename + extension to use for the export file. The default is the
            filename sans extension of the original SEM file, with 
            '_exported.png' appended.
        preprocess : callable, optional
            callable to pre-process the image before any other processing is 
            done, useful for e.g. smoothing. Must take and return a 
            numpy.ndarray containing the image data as only arguments, and must
            not change e.g. the pixel size or the scale bar may be incorrectly 
            sized. The default is None.
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
            is `0.8`.
        invert : bool, optional
            If `True`, a white scalebar and text on a black box are used. The 
            default is `False` which gives black text on a white background.
        boxpad : int, optional
            size of the space/padding around the box (with respect to the sides
            of the image) in printer points. The default is 10.
        store_settings : bool, optional
            when `True`, a .txt file is saved along with the image containing
            all settings passed to this function. The default is False
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
            raise ValueError('overwriting original SEM file not recommended, '
                             'use a different filename for exporting.')
              
        #get and display image
        try:
            exportim = self.image.copy()
        except AttributeError:
            exportim = self.get_image().copy()
        
        #call main export_with_scalebar function with correct pixelsize etc
        from .utility import _export_with_scalebar
        _export_with_scalebar(exportim, pixelsize, unit, filename, **kwargs)


class ZeissSEM:
    """
    Class with convenience functions for the Zeiss EVO and Gemini SEMs. By 
    default does not load the image into memory.
    
    Parameters
    ----------
    filename : str
        filename of the image to load. The file extension may be but is not 
        required to be included.
        
    Returns
    -------
    ZeissSEM class instance
    """
    def __init__(self,filename):
        #raise error if wrong format or file does not exist
        if type(filename) != str:
            raise TypeError('filename must be a string')
        if os.path.exists(filename):
            self.filename = filename
        elif os.path.exists(filename+'.tif'):
                self.filename = filename + '.tif'
        else:
            raise FileNotFoundError('The file "'+filename+'" could not be '
                                    'found.')
        self.PIL_image = Image.open(self.filename)

    
    def get_image(self):
        """loads the image data
        
        Returns
        -------
        PIL.Image instance
        """
        self.image = np.array(self.PIL_image)
        self.shape = np.shape(self.image)
        return self.image
    
    def get_metadata(self):
        """extracts embedded metadata from the image file"""
        #don't reread if we already have it
        if hasattr(self,'metadata'):
            return self.metadata
        
        #get correct tiftags from 
        tifftags = self.PIL_image.tag
        metadata = tifftags[34118][0].split('\r\n')
        
        #ignore numeric lines at the start
        metadata = [line for line in metadata if not line[:1].isdigit()]
        
        #construct xml object
        import xml.etree.ElementTree as et
        xml_root = et.Element('MetaData')
        
        #make sure the first child exists
        if '=' in metadata[0]:
            child = et.SubElement(xml_root, 'None')
        
        #add (nested) items in loop over lines
        for line in metadata:
            if line:#skip empty
                if not '=' in line:
                    child = et.SubElement(xml_root, line.strip())
                else:
                    key,val = line.split(' = ')
                    subchild = et.SubElement(child, key.strip())
                    subchild.text = val.strip()

        self.metadata = xml_root
        return self.metadata
        
    def print_metadata(self):
        """print formatted output of metadata"""
        
        try:
            xml_root = self.metadata
        except AttributeError:
            xml_root = self.get_metadata()
        
        util.print_metadata(xml_root)

    def get_pixelsize(self):
        """
        gets the physical size of a pixel from the metadata

        Returns
        -------
        pixelsize : float
            physical size of the pixels in x and y
        unit : str
            physical unit corresponding to the pixelsize.

        """   
        metadata = self.get_metadata()
        pixelsize,unit = metadata.find('AP_IMAGE_PIXEL_SIZE')\
            .find('Image Pixel Size').text.split()
        
        return float(pixelsize), unit
        
    def export_with_scalebar(self, filename=None, **kwargs):
        """
        saves an exported image of the SEM image with a scalebar in one of the 
        four corners, where barsize is the scalebar size in data units (e.g. 
        nm) and scale the overall size of the scalebar and text with respect to
        the width of the image.

        Parameters
        ----------
        filename : string or `None`, optional
            Filename + extension to use for the export file. The default is the
            filename sans extension of the original SEM file, with 
            '_exported.png' appended.
        preprocess : callable, optional
            callable to pre-process the image before any other processing is 
            done, useful for e.g. smoothing. Must take and return a 
            numpy.ndarray containing the image data as only arguments, and must
            not change e.g. the pixel size or the scale bar may be incorrectly 
            sized. The default is None.
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
            may be used just to crop and rescale. The default is `True`.
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
            is `0.8`.
        invert : bool, optional
            If `True`, a white scalebar and text on a black box are used. The 
            default is `False` which gives black text on a white background.
        boxpad : int, optional
            size of the space/padding around the box (with respect to the sides
            of the image) in printer points. The default is 10.
        store_settings : bool, optional
            when `True`, a .txt file is saved along with the image containing
            all settings passed to this function. The default is False
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
            raise ValueError('overwriting original SEM file not recommended, '
                             'use a different filename for exporting.')
              
        #get and display image
        try:
            exportim = self.image.copy()
        except AttributeError:
            exportim = self.get_image().copy()
        
        #call main export_with_scalebar function with correct pixelsize etc
        from .utility import _export_with_scalebar
        _export_with_scalebar(exportim, pixelsize, unit, filename, **kwargs)