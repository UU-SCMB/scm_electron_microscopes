import numpy as np
import os
from PIL import Image
from warnings import warn,filterwarnings

class tia:
    """
    Set of convenience functions for electron microscopy images of the tecnai
    12, 20, 20feg and Talos microscopes when using the TIA software and 
    exporting the images as .tif files from TIA. Initializing the class takes a
    string containing the filename as only argument, and by default loads in 
    the image.
    
    Parameters
    ----------
    filename : string
        name of the file to load. Can but is not required to include .tif
        as extension.
        
    Attributes
    ----------
    filename : string
        name of the image file
    image : np.ndarray
        array of pixel values of the image with the optional data/scale bar 
        cropped off
    scalebar : numpy.ndarray
        if present, the array of pixel values of the original data/scale bar
    shape : tuple
        shape in (y,x) pixels of the image array
    dtype : numpy.dtype
        data type of the pixel values, generally `unint8` or `uint16`
    PIL_image : PIL.Image
        python imaging library Image object of the image file
        
    Returns
    -------
    `tia` class instance 
    """
    
    def __init__(self,filename):
        #raise error if wrong format or file does not exist
        if type(filename) != str:
            raise TypeError('`filename` must be of type `str`')
        if not os.path.exists(filename):
            if os.path.exists(filename + '.tif'):
                filename = filename + '.tif'
            else:
                raise FileNotFoundError(f'The file "{filename}" could not be'
                                        ' found.')
        
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
        convert : str, one of [`fm`,`pm`,`Å`,'A',`nm`,`um`,`µm`,`mm`,`cm`,`dm`,`m`], optional
            physical unit to use for the pixel size. The default is None, which
            chooses one of the above automatically based on the value.
        
        Returns
        -------
        pixelsize : float
            the physical size of a pixel in the given unit
        unit : str
            physical unit of the pixel size
        """
        #tiff tags 65450 to 65452 give the x resolution, y resolution and unit
        #similar to how tiff tags 2822, 283 and 296 are defined in the tiff 
        #specification. Specifically, a two-tuple of ints giving pixels per `n` 
        #resolution units, e.g. 586350674 pixels per 100 resolution units is 
        #encoded as (586350674, 100) and gives 1.7 nm/pixel. Tag 65452 gives 
        #the unit and is 1 for no unit, 2 for inch and 3 for cm
        if all([t in self.PIL_image.tag for t in [65450,65451,65452]]):
            pixelsize_x = self.PIL_image.tag[65450][0]
            pixelsize_y = self.PIL_image.tag[65451][0]
            baseunit = self.PIL_image.tag[65452][0]
        
        #old tecnai 10 uses different software requiring different class (sis)
        elif 33560 in self.PIL_image.tag:
            raise KeyError('pixel size not encoded in file but your image '
                           'looks like an Olympus SIS tiff. Did you mean to '
                           'use the `sis` class for e.g. the tecnai 10?')
        
        #check for ImageJ metadata format, as ImageJ overwrites metadata
        elif 270 in self.PIL_image.tag and 'ImageJ' in self.PIL_image.tag[270][0]:
            warn('it looks like the image was modified in ImageJ, metadata may'
                 ' not be correct',stacklevel=2)
            from .utility import _convert_length
            pixelsize_x = self.PIL_image.tag[282][0]
            pixelsize_y = self.PIL_image.tag[283][0]
            unit = self.PIL_image.tag[270][0].split('unit=')[1].split('\n')[0]
            if '\\u00B5' in unit:#replace micro character
                unit = unit.replace('\\u00B5','µ')
            fact = _convert_length(1, unit, 'cm')[0]#convert baseunit to px/cm
            pixelsize_x = (pixelsize_x[0],pixelsize_x[1]*fact)
            pixelsize_y = (pixelsize_y[0],pixelsize_y[1]*fact)
            baseunit = 3
            
        #old tecnai 12 images have it in the standard keys 282 and 283 instead
        elif all([t in self.PIL_image.tag for t in [282,283,296]]):
            warn('pixel size metadata in unusual format, value may be '
                 'incorrect',stacklevel=2)
            pixelsize_x = self.PIL_image.tag[282][0]
            pixelsize_y = self.PIL_image.tag[283][0]
            baseunit = self.PIL_image.tag[296][0]
            
        #otherwise set the baseunit to 1 for 'no unit' to fall back to legacy
        else:
            baseunit = 1

        #check unit encoding and convert pixels per n baseunit to meter/pixel
        if baseunit==2:#pixels per inch
            pixelsize_x = 2.54e-2*pixelsize_x[1]/pixelsize_x[0]
            pixelsize_y = 2.54e-2*pixelsize_y[1]/pixelsize_y[0]
        elif baseunit==3:#pixels per cm
            pixelsize_x = 1e-2*pixelsize_x[1]/pixelsize_x[0]
            pixelsize_y = 1e-2*pixelsize_y[1]/pixelsize_y[0]
        else:#try and fall back to legacy calibration by reading the scale bar
            warn('unknown pixel size or unit, falling back to '
                 'tia.get_pixelsize_legacy()',stacklevel=2)
            from .utility import _convert_length
            pixelsize_x,unit = self.get_pixelsize_legacy()
            baseunit = 3
            pixelsize_x = [1/_convert_length(pixelsize_x,unit,'cm')[0],1]
            pixelsize_y = pixelsize_x
        
        #find the right unit and rescale for convenience
        if convert is None:
            if pixelsize_x >= 1e-3:
                unit = 'm'
            elif pixelsize_x < 1e-3 and pixelsize_x >= 1e-6:
                unit = 'mm'
                pixelsize_x = 1e3*pixelsize_x
                pixelsize_y = 1e3*pixelsize_y
            elif pixelsize_x < 1e-6 and pixelsize_x >= 1e-9:
                unit = 'µm'
                pixelsize_x = 1e6*pixelsize_x
                pixelsize_y = 1e6*pixelsize_y
            elif pixelsize_x < 1e-9 and pixelsize_x >= 1e-12:
                unit = 'nm'
                pixelsize_x = 1e9*pixelsize_x
                pixelsize_y = 1e9*pixelsize_y
            else:
                unit = 'pm'
                pixelsize_x = 1e12*pixelsize_x
                pixelsize_y = 1e12*pixelsize_y
        #else use given unit
        else:
            from .utility import _convert_length
            pixelsize_x,unit = _convert_length(pixelsize_x, 'm', convert)
            pixelsize_y,unit = _convert_length(pixelsize_y, 'm', convert)
            
        #store and return
        if pixelsize_x != pixelsize_y:
            warn('x and y pixelsize not the same, only x pixelsize returned',
                 stacklevel=2)
        self.pixelsize = pixelsize_x
        self.unit = unit
        return (self.pixelsize,unit)
    
    def get_pixelsize_legacy(self, debug=False, use_legacy_measurement=False):
        """
        .. deprecated::
           This function has been deprecated and may give slightly inaccurate 
           result (only accurate to the nearest whole pixel), use 
           `tia.get_pixelsize()` for more accurate and faster calibration. 
           Included for cases where results using the previous calibration 
           method must be reproduced or compared with.
        
        Reads the scalebar from images of the Tecnai or Talos  TEM microscopes 
        using text recognition via pytesseract or with manual input when 
        pytesseract is not installed

        Parameters
        ----------
        debug : bool, optional
            enable debug mode which prints extra information and figures to
            troubleshoot any issues with calibration. The default is False.
        use_legacy_measurement : bool, optional
            if `True`, use the (incorrect) left-side to left-side distance of 
            the vertical lines of the scale bar (i.e. equal to the 
            centre-to-centre distance of the vertical parts of the line). This
            was long thought to be the correct way to interpret the scale bar 
            and is available for backwards compatability with older data 
            (analysis). The default is `False`, which uses the outermost white 
            pixels of the scale bar, i.e. from the leftmost row of white pixels
            of the left vertical part to the rightmost row of the right 
            vertical part.

        Returns
        -------
        pixelsize : float
            the pixelsize in calibrated (physical) units
        unit : string
            the physical unit of the pixelsize

        """
        import re
        import cv2
        
        #this is even more redundant where you have to give the pixelsize
        if len(self.scalebar) == 0:
            warn('original scale bar not found!')
            pixelsize = float(input('Please give pixelsize in nm: '))
            self.unit = 'nm'
            self.pixelsize = pixelsize
            return pixelsize,'nm'
        #find contour corners of objects sorted left to right, first item in 
        #corners is scale bar, rest is from text
        else:
            sb = self.scalebar
            if self.dtype != np.uint8:
                sb = ((sb-sb.min())/((sb.max()-sb.min())/255)).astype(np.uint8)
            if int(cv2.__version__[0]) >= 4:
                corners,_ = cv2.findContours(sb,cv2.RETR_LIST,
                                             cv2.CHAIN_APPROX_SIMPLE)
            else:
                _,corners,_ = cv2.findContours(sb,cv2.RETR_LIST,
                                               cv2.CHAIN_APPROX_SIMPLE)
            corners = sorted(corners, key=lambda c: cv2.boundingRect(c)[0])
        
        #length in pixels between top left corners of vertical bars
        if use_legacy_measurement:
            usecorners = [0,10]
        else:
            usecorners = [0,9]
        barlength = corners[0][usecorners[1],0,0]-corners[0][usecorners[0],0,0]
        
        if debug:
            import matplotlib.pyplot as plt
            print('\n------- DEBUGGING IMAGE CALIBRATION -------')
            print('- length:',barlength,'pixels')
            plt.figure('[DEBUG MODE] scale bar corners')
            plt.imshow(self.scalebar)
            plt.scatter(corners[0][:,0,0],corners[0][:,0,1],color='r',
                        label='corners')
            plt.scatter(corners[0][usecorners,0,0],corners[0][usecorners,0,1],
                        color='green',label='used for calibration')
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
                cv2.threshold(bartext,0,255,
                              cv2.THRESH_BINARY+cv2.THRESH_OTSU)[1],
                np.ones((5,5),np.uint8)
            )
            if debug:
                print('- preprocessing text, resizing text image from',
                      bartextshape,'to',np.shape(bartext))
        
        try:
            #load tesseract-OCR for reading the text
            import pytesseract
            
            #switch error handling from a ValueError (we may also raise later
            #in case of text recognition problems) to one we can only raise 
            #here, so we can give the correct warning
            try:
                tesseract_version = float(str(
                    pytesseract.get_tesseract_version())[:3])
            except ValueError:
                raise FileNotFoundError
            
            #settings vary per version, so use tesseract_verion to use correct
            if tesseract_version <= 4.0:
                text = pytesseract.image_to_string(
                    bartext,
                    config="--oem 0 -c tessedit_char_whitelist=0123456789pnuµm --psm 7"
                )
                #oem 0 selects older version of tesseract which still takes 
                #the char_whitelist param
                #tessedit_char_whitelist takes list of characters it searches 
                #for (to reduce reading errors)
                #psm 7 is a mode that tells tesseract to assume a single line 
                #of text in the image
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
            warn('pytesseract not installed, defaulting to manual mode',
                 stacklevel=1)
            unit = input('give scale bar unit: ')
            value = float(input('give scale bar size in '+unit+': '))
        except FileNotFoundError:
            warn('tesseract OCR engine was not found by pytesseract. Switching'
                 ' to manual mode.',stacklevel=2)
            unit = input('give scale bar unit: ')
            value = float(input('give scale bar size in '+unit+': '))
        except:
            warn('could not read scale bar text, perhaps try debug=True. '
                 'Switching to manual mode.',stacklevel=2)
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
        preprocess : callable, optional
            callable to pre-process the image before any other processing is 
            done, useful for e.g. smoothing. Must take and return a 
            numpy.ndarray containing the image data as only arguments, and must
            not change e.g. the pixel size or the scale bar may be incorrectly 
            sized. The default is None.
        crop : tuple or `None`, optional 
            range describing a area of the original image (before rescaling the
            resolution) to crop out for the export image. Can have two forms:
                
            - `((xmin,ymin),(xmax,ymax))`, with the integer pixel indices of 
            the top left and bottom right corners respectively.
                
            - `(xmin,ymin,w,h)` with the integer indices of the top left corner
            and the width and heigth of the cropped image in pixels (prior to 
            optional rescaling using `resolution`). When this format is used,
            it is possible to set the width and height in pixels (default) or 
            in data units via the `crop_unit` parameter.
            
            The default is `None` which takes the entire image.
        crop_unit : `'pixels'` or `'data'`, optional
            sets the unit in which the width and height in `crop` are 
            specified when using the (x,y,w,h) format, with `'pixels'` to give 
            the size in pixels or `'data'` to specify the size in the physical 
            unit used for the scalebar (after optional unit conversion via the 
            `convert` parameter). Note that the position of the top left corner
            is given in pixels. The `((xmin,ymin),(xmax,ymax))` format must be
            always given in pixels, and `crop_unit` is ignored if `crop` is 
            given in this format. The default is `'pixels'`.
        intensity_range : tuple or `None` or `'automatic'`, optional
            tuple of `(lower,upper)` ranges for the (original) pixel values to 
            scale the brightness/contrast in the image to, or `'automatic'` to 
            autoscale the intensity to the 0.01th and 99.99th percentile of the 
            input image, or None for the min and max value in the original 
            image. The default is `None`.
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
        convert : str, one of [`'fm'`,`'pm'`,`'Å'` or `A`,`'nm'`,`'µm'` or `'um'`,`'mm'`,`'cm'`,`'dm'`,`'m'`]
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
            vertical offset for the baseline of the scale bar text from the top
            of the scale bar, in printer points. The default is 10.
        fontpad : int, optional
            minimum size in printer points of the space/padding between the 
            text and the bar and surrounding box. The default is 10.
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
            raise ValueError('overwriting original TEM file not reccomended, '+
                             'use a different filename for exporting.')
        
        #get image
        exportim = self.image.copy()
        
        #call main export_with_scalebar function with correct pixelsize etc
        from .utility import _export_with_scalebar
        _export_with_scalebar(exportim, pixelsize, unit, filename, **kwargs)
        
        
class velox:
    """
    Class for importing the .emd file format used natively by the Velox 
    software used on the Talos microscopes.
    
    Note that one .emd file may contain multiple images / videos, (e.g. when
    recording with multiple detectors simultaneously), and most functions are
    available through the `velox_image` subclass accessible through the 
    `get_image` function.
    
    Parameters
    ----------
    filename : str or int
        The filename to load, extension optional. Alternatively an integer may
        be given to load the nth file in the current working directory. The
        default is to load the first file.
    quiet : bool
        whether to print a list of images contained in the file when the class
        is initialized. The default is False.
    
    Returns
    -------
    `velox` class instance 
    """
    def __init__(self,filename=None,quiet=False):
        """init class instance, open file container"""
        import h5py
        
        #optionally give None to find first emd file in folder
        if filename is None:
            filename = 0
        
        #can also load nth file in folder
        if type(filename)==int:
            from glob import glob
            filenames = glob('*.emd')
            try:
                filename = filenames[filename]
            except IndexError:
                raise FileNotFoundError(f'{len(filenames)} .emd files were '
                    f'found in current working directory, index {filename} is'
                    ' out of bounds')
        
        #load the file, if not found try appending file extension
        try:
            self._emdfile = h5py.File(filename,'r')
        except FileNotFoundError:
            try:
                self._emdfile = h5py.File(filename+'.emd','r')
                filename = filename+'.emd'
            except FileNotFoundError:
                raise FileNotFoundError(f"the file '{filename}' was not found")
        
        self.filename = filename
        
        self.data_list =  []
        self.data_names = []
        self._data_type = []
        
        i = 0
        for key,val in self._emdfile['Data'].items():
            for v in val.values():
                #if 'Data' in v:
                if key in ['Image','SpectrumStream']:
                    self.data_list.append(v)
                    self.data_names.append(key+f'{i:03d}')
                    self._data_type.append(key)
                    i+=1
        
        self._len = len(self.data_list)
        
        if not quiet:
            print(self)
    
    def __del__(self):
        """on destruction of class instance, close the file"""
        self._emdfile.close()
    
    def __repr__(self):
        """represents class instance in terminal"""
        return f"scm_electron_microscopes.velox('{self.filename}')"
    
    def __str__(self):
        """string method for printing class instance"""
        s = self.__repr__()+'\n'
        for i,n in enumerate(self.data_names):
            imshape = self.data_list[i]['Data'].shape
            s+=f"{i}: name='{n}', shape={imshape}\n"
        return s[:-1]#strips last newline
    
    def __len__(self):
        """allows for `len(velox)` to return number of images"""
        return self._len
        
    def __getitem__(self,i):
        """make class indexable by returning image"""
        if i >= len(self):
            raise IndexError(f'index {i} out of bounds for {len(self)} images')
        return self.get_dataset(i)
    
    def get_dataset(self,dataset):
        """Returns velox_image class instance containing all data and metadata
        for a particular image in the file.
        
        Parameters
        ----------
        image : str or int
            the image to return the data for, given as the name/tag (when str)
            or as its integer index in the file, i.e. `velox.get_image(0)` 
            returns the data container for the first image.
        
        Returns
        -------
        `velox_dataset` or `velox_image` class instance
        """
        #allow for dataset index as well as its name/tag
        if type(dataset) == str:
            dataset = self.data_names.index(dataset)
        
        if self._data_type[dataset] == 'Image':
            return velox_image(self,dataset)
        elif self._data_type[dataset] == 'SpectrumStream':
            return velox_edx(self,dataset)
        else:
            return velox_dataset(self,dataset)
    
    def print_file_struct(self):
        """prints a formatted overview of the structure of the .emd file 
        container, useful for accessing additional data manually"""
        self._recursive_struct_print(self._emdfile)

    def _recursive_struct_print(self,root,prefix='|'):
        """see `print_file_struct"""
        for i in root:
            #safeguard against infinite recursion
            if len(prefix)>20:
                print(prefix+'-MAX RECURSION DEPTH')
            
            #for a tag, print and call function on child
            elif type(i)==str:
                print(prefix+i)
                if len(root[i])>0:
                    self._recursive_print(root[i],prefix=prefix+'-')
            
            #for data, print the root data __repr__ method
            else:
                print(prefix+f'-{root.__repr__()}')
                break

class velox_dataset:
    """
    general subclass for individual datasets of a velox file, acts 
    mainly as intermediate to the specific subclasses
    """
    def __init__(self,parent,im):        
        #store some properties of the velox class parent and keep a reference
        self._parent = parent
        self._emdfile = parent._emdfile
        self._imageData = parent.data_list[im]
        
        #store public attributes
        self.filename = parent.filename
        self.name = parent.data_names[im]
        self.data_type = parent._data_type[im]
        self.index = im
        self.shape = self._imageData['Data'].shape
        self.dtype = self._imageData['Data'].dtype
    
    def get_raw_data(self):
        """
        returns a reference to the raw data of the dataset (without any 
        re-indexing being applied or so)
        """
        return self._imageData['Data']

    def get_metadata(self,i=0):
        """extracts the metadata corresponding to the image as JSON dict
        
        Returns
        -------
        dict containing the metadata
        """
        #only need to read once, otherwise just return from previous read
        if hasattr(self,'metadata'):
            return self.metadata
        
        #load metadata as int numpy array and convert back to bytes, this is
        #because the datatype is incorrectly listed as int in the HDF5 file. By
        #default a large block is reserved in the file, unused space contains
        #trailing zeros, have to be stripped before it can be converted by JSON
        metadata = np.trim_zeros(self._imageData['Metadata'][:,i]).tobytes()
        
        #convert json to dict and store
        import json
        self.metadata = json.loads(metadata)
        return self.metadata

    def get_detector(self):
        """
        Returns metadata for the detector which was used to take this image
        
        Returns
        -------
        dict
        """
        md = self.get_metadata()
        try:
            det = md['Detectors']['Detector-'+md['BinaryResult']['DetectorIndex']]
        except KeyError:
            det = md['BinaryResult']['Detector']
            flag = True
            for d in md['Detectors'].values():
                if det in d['DetectorName']:
                    det = d
                    flag = False
                    break
            if flag:
                raise KeyError('No detector data found')
        return det
    
    def print_metadata(self):
        """prints formatted output of the file's metadata"""
        metadata = self.get_metadata()
        
        #don't print anything when metadata is empty
        if metadata is None or len(metadata) == 0:
            warn('no metadata found',stacklevel=2)
            return
        
        #print header, contents and footer
        print('\n-----------------------------------------------------')
        print('METADATA')
        print(self.filename)
        print('-----------------------------------------------------')
        for key,val in metadata.items():
            if isinstance(val,dict):
                print('\n'+key+':')
                self._recursive_md_print(val)
            else:
                print('\n'+key+': '+val)
        print('-----------------------------------------------------\n')
    
    def _recursive_md_print(self,root,prefix='|'):
        """see `print_file_struct"""
        for key,val in root.items():
            #safeguard against infinite recursion
            if len(prefix)>20:
                print(prefix+'-MAX RECURSION DEPTH')
            
            #for a tag, print and call function on child
            elif isinstance(val,dict):
                print(prefix+key+':')
                self._recursive_md_print(val,prefix=prefix+'-')
            
            #for data, print the root data __repr__ method
            else:
                print(prefix+key+': '+val)

class velox_image(velox_dataset):
    """
    Subclass of the `velox_dataset` class for individual images (or image 
    series) in an .emd file, such as when simultaneously recording HAADF-STEM 
    and BF-STEM. Not indended to be called directly, rather to be initialized 
    trough the `get_image` method of the `scm_electron_microscopes.velox` 
    class.
    
    Parameters
    ----------
    filename : str
        the .emd file to take the image from
    im : str or int
        name / tag or integer index of the image to initialize
    """
    def __init__(self,parent,im):
        #init parent class and get attribs
        super().__init__(parent,im)
        
        #change dim order to (frame,y,x) and store length as number of frames
        self.shape = (self.shape[-1],*self.shape[:-1])
        self._len = self.shape[0]

    def __repr__(self):
        return f"scm_electron_microscopes.velox_image('{self.filename}','{self.name}')"

    def __len__(self):
        """add no. video frames as length"""
        return self._len
            
    def __getitem__(self,i):
        """make class indexable by returning appropriate video frame"""
        return self.get_frame(i)
    
    def __iter__(self):
        """initialize iterator for next function"""
        self._iter_n = 0
        return self

    def __next__(self):
        "make iterable where it returns one image at a time"
        #make sure __iter__ has been called
        if not hasattr(self,'_iter_n'):
            self.__iter__()
        
        #increment iterator before return call
        self._iter_n += 1
        
        #check end condition or return using __getitem__
        if self._iter_n > len(self):
            raise StopIteration
        else:
            return self[self._iter_n-1]

    def get_data(self):
        """Loads and returns the full image data as numpy array
        
        Returns
        -------
        numpy.ndarray of pixel value
        s"""
        #note that loading per image is faster than loading the entire array
        #as it is stored in a different byte order than used in the HDF5 file
        
        rawdata = self.get_raw_data()
        return np.array(
            [rawdata[:,:,i] for i in range(len(self))]
        )

    def get_frame(self,i):
        """returns specific image / video frame from the dataset
        
        Parameters
        ----------
        i : int
            the index of the frame to load
        
        Returns
        -------
        numpy.array of pixel values
        """
        if i >= len(self):
            raise IndexError(f'index {i} does not fit in length {len(self)}')
        return self.get_raw_data()[...,i] 
    
    def get_pixelsize(self,convert=None):
        """
        returns the pixel size from the metadata, rescaled to an appropriate 
        unit for convenience
        
        Parameters
        ----------
        convert : one of ['pm', 'nm', 'µm', 'um', 'mm', 'm']
            physical data unit to convert the pixel size to, the default is 
            None which chooses a unit based on the magnitude.
        
        Returns
        -------
        pixelsize : tuple of float
            (y,x) pixel sizes
        unit : str
            physical unit of the pixel size
        """
        md = self.get_metadata()['BinaryResult']
        pixelsize = md['PixelSize']
        pixelsize = [float(pixelsize['height']),float(pixelsize['width'])]
        unit = [md['PixelUnitY'],md['PixelUnitX']]
        
        #if no unit is given, determine from y-pizelsize
        if convert is None:
            if pixelsize[0] >= 10e-3:
                convert = 'm'
            elif pixelsize[0] < 10e-3 and pixelsize[0] >= 10e-6:
                convert = 'mm'
            elif pixelsize[0] < 10e-6 and pixelsize[0] >= 10e-9:
                convert = 'µm'
            elif pixelsize[0] < 10e-9 and pixelsize[0] >= 10e-12:
                convert = 'nm'
            else:
                convert = 'pm'
            
        #convert unit
        from .utility import _convert_length
        for i in range(len(pixelsize)):
            pixelsize[i] = _convert_length(pixelsize[i], unit[i], convert)[0]

        #store and return
        self.pixelsize = pixelsize
        self.unit = convert
        
        return self.pixelsize,self.unit
    
    def get_frametime(self):
        """
        Returns the time in seconds it takes to scan one frame
        
        Returns
        -------
        float
        """
        return float(self.get_metadata()['Scan']['FrameTime'])
    
    def export_tiff(self,filename_prefix=None,frame_range=None,**kwargs):
        """
        stores the image data to a tiff file with metadata stored in the image
        description for futher processing or viewing in other software.

        Parameters
        ----------
        filename_prefix : str
            filename to use for saved file without file extension 
        frame_range : int or tuple of int
            int specifying which frame, or tuple of (start,stop) ints
            specifying which frames, to save in the tiff file. The default is
            all frames in the dataset
        kwargs : dict
            any further keyword arguments will be passed on to 
            `tifffile.imsave`.

        Returns
        -------
        None.

        """
        from tifffile import imsave,memmap
        
        #default file name
        if filename_prefix is None:
            filename = self.filename[:-4]+'_'+self.name+'.tiff'
        else:
            filename = filename_prefix+'.tiff'
        
        #default to full frame range
        if frame_range is None:
            if len(self) == 1:
                frame_range = 0
            else:
                frame_range = (0,len(self))
        
        #get pixels per cm for the .tiff XResolution and YResolution tags 
        # (tag 282 and 283) and ResolutionUnit (tag 296)
        pixelsize = self.get_pixelsize(convert='cm')[0]
        pixels_per_cm = (
            int(1/(pixelsize[1])),
            int(1/(pixelsize[0]))
        )
        
        #save single image directly
        if isinstance(frame_range,int):
            imsave(
                filename,
                data = self.get_frame(frame_range),
                metadata = self.get_metadata(frame_range),
                resolution = (*pixels_per_cm,'CENTIMETER'),
                software = 'scm_electron_miscroscopes.py',
                **kwargs
            )
    
        else:
            #allocate empty file of correct shape
            imsave(
                filename,
                shape=(len(range(*frame_range)),*self.shape[1:]),
                dtype=self.dtype,
                metadata=self.get_metadata(),
                resolution = (*pixels_per_cm,'CENTIMETER'),
                software = 'scm_electron_miscroscopes.py',
                **kwargs
            )
            
            #write data to file iteratively to avoid loading all to memory
            file = memmap(filename)
            for i,j in enumerate(range(*frame_range)):
                file[i] = self.get_frame(j)
                file.flush()
    
    
    def export_with_scalebar(self, frame=0, filename=None, **kwargs):
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
        frame : int
            the frame to export, see `get_frame()`. The default is 0.
        preprocess : callable, optional
            callable to pre-process the image before any other processing is 
            done, useful for e.g. smoothing. Must take and return a 
            numpy.ndarray containing the image data as only arguments, and must
            not change e.g. the pixel size or the scale bar may be incorrectly 
            sized. The default is None.
        crop : tuple or `None`, optional 
            range describing a area of the original image (before rescaling the
            resolution) to crop out for the export image. Can have two forms:
                
            - `((xmin,ymin),(xmax,ymax))`, with the integer pixel indices of 
            the top left and bottom right corners respectively.
                
            - `(xmin,ymin,w,h)` with the integer indices of the top left corner
            and the width and heigth of the cropped image in pixels (prior to 
            optional rescaling using `resolution`). When this format is used,
            it is possible to set the width and height in pixels (default) or 
            in data units via the `crop_unit` parameter.
            
            The default is `None` which takes the entire image.
        crop_unit : `'pixels'` or `'data'`, optional
            sets the unit in which the width and height in `crop` are 
            specified when using the (x,y,w,h) format, with `'pixels'` to give 
            the size in pixels or `'data'` to specify the size in the physical 
            unit used for the scalebar (after optional unit conversion via the 
            `convert` parameter). Note that the position of the top left corner
            is given in pixels. The `((xmin,ymin),(xmax,ymax))` format must be
            always given in pixels, and `crop_unit` is ignored if `crop` is 
            given in this format. The default is `'pixels'`.
        intensity_range : tuple or `None` or `'automatic'`
            tuple of `(lower,upper)` ranges for the (original) pixel values to 
            scale the brightness/contrast in the image to, or `'automatic'` to 
            autoscale the intensity to the 0.01th and 99.99th percentile of the 
            input image, or None for the min and max value in the original 
            image. The default is `None`.
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
        convert : str, one of [`'fm'`,`'pm'`,`'Å'` or `A`,`'nm'`,`'µm'` or `'um'`,`'mm'`,`'cm'`,`'dm'`,`'m'`], optional
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
            vertical offset for the baseline of the scale bar text from the top
            of the scale bar, in printer points. The default is 10.
        fontpad : int, optional
            minimum size in printer points of the space/padding between the 
            text and the bar and surrounding box. The default is 10.
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
        #note we only pass the x pixelsize to the scalebar function
        try:
            pixelsize,unit = self.pixelsize,self.unit
        except AttributeError:
            pixelsize,unit = self.get_pixelsize()
        
        #set default export filename
        if type(filename) != str:
            filename = self.filename.rpartition('.')[0]+\
                f'_image-{self.index:02d}_scalebar.png'
        
        #check we're not overwriting the original file
        if filename==self.filename:
            raise ValueError('overwriting original file not reccomended, '
                             'use a different filename for exporting.')
        
        #get image
        exportim = self.get_frame(frame)
        
        #call main export_with_scalebar function with correct pixelsize etc
        from .utility import _export_with_scalebar
        _export_with_scalebar(exportim, pixelsize[1], unit, filename, **kwargs)
        
        
class velox_edx(velox_dataset):
    """
    subclass for emd files with edx data
    """
    def __init__(self,parent,im):
        #init parent class and get attribs
        super().__init__(parent,im)
        
        #change dim order to (frame,y,x) and store length as number of frames
        self.shape = (self.shape[-1],*self.shape[:-1])
        self._len = self.shape[0]
        self._pixelflag = 2**16-1
    
    def get_image(self,energy_ranges=None,frame_range=None,binning=1):
        """
        returns edx/eds image where the pixel value is the total number of 
        photon counts within the specified energy range(s) and frame range.

        Parameters
        ----------
        energy_ranges : list of tuples, optional
            List of (min,max) energy range(s) specifying which photons to 
            count, given in keV. The default is None which takes all photon 
            counts.
        frame_range : tuple, optional
            Tuple of (min,max) for the frame indices to sum the counts for. The
            default is None which sums all frames.

        Returns
        -------
        2D numpy.array

        """
        framelocs = list(self._imageData['FrameLocationTable'][:,0])
        
        md = self.get_metadata()
        nx = int(md['Scan']['ScanSize']['width'])
        ny = int(md['Scan']['ScanSize']['height'])
        #nf = len(framelocs)
        #ne = 2**12#this is hardcoded for now, cannot find it in metadata
        
        pixelflag = self._pixelflag
        
        det_md = self.get_detector()
        energy_offset = float(det_md['OffsetEnergy'])/1000
        energy_step = float(det_md['Dispersion'])/1000
        energy_start = float(det_md['BeginEnergy'])/1000
        
        rawdata = self.get_raw_data()
        
        if not frame_range is None:
            start,stop = frame_range
            framelocs = framelocs+[len(rawdata)]
            rawdata = rawdata[framelocs[start]:framelocs[stop]]
        else:
            rawdata = rawdata[:]
        
        
        #when specific energy ranges are specified,take flag values and 'or'
        # each range onto the boolean mask
        if not energy_ranges is None:
            mask = rawdata==pixelflag
            for start,stop in energy_ranges:
                start = (start-energy_offset)/energy_step
                stop = (stop-energy_offset)/energy_step
                mask = np.logical_or(
                    mask,
                    np.logical_and(start<=rawdata,rawdata<stop)
                )
            rawdata = rawdata[mask]
        
        #otherwise skip just values below the energy_start value
        else:
            rawdata = rawdata[
                (rawdata==pixelflag)|(rawdata>=energy_start)
            ]
        
        from numba import jit
        @jit()
        def _construct_spectrumim(stream):
            res = np.zeros((ny//binning,nx//binning),dtype=np.uint16)
            x = 0
            y = 0
            #loop over all stream values
            for i,v in enumerate(stream):
                #if new pixel flag, increment x
                if v == pixelflag:
                    x += 1
                    if x == nx:#if imwidth reached, reset x and incr y
                        x = 0
                        y += 1
                        if y == ny:#if imheight reached, reset y
                            y = 0
                else:
                    res[y//binning,x//binning] += 1
            
            return res
        
        return _construct_spectrumim(rawdata)
    
    def get_spectrum(self):
        """
        get overall spectral data for the edx dataset

        Returns
        -------
        energies : numpy.array
            energies in keV
        counts : numpy.array
            number of photon counts per energy

        """
        #get calibrations
        det_md = self.get_detector()
        energy_offset = float(det_md['OffsetEnergy'])/1000
        energy_step = float(det_md['Dispersion'])/1000
        #energy_start = float(det_md['BeginEnergy'])/1000
        
        #make list of energy values
        energies = np.arange(2**12)*energy_step + energy_offset
        #mask = energies>=energy_start
        #energies = energies[mask]
        
        if 'Spectrum' in self._emdfile['Data']:
            spectrum = self._emdfile['Data/Spectrum']
            counts = spectrum[list(spectrum.keys())[0]]['Data'][:,0][:]
        else:
            data = self.get_raw_data()[:]
            counts = np.bincount(data[data!=2**16-1],minlength=2**12)
       
        return energies,counts
            
     

class sis:
    """
    Set of convenience functions for electron microscopy images of the now 
    defunct tecnai 10 microscope which operated the Olympus Soft Imaging System
    software (analySIS) which exported to .tif. Initializing the class takes a
    string containing the filename as only argument, and by default loads in 
    the image.
    
    Parameters
    ----------
    filename : string
        name of the file to load. Can but is not required to include .tif
        as extension.
    """
    
    def __init__(self,filename):
        #raise error if wrong format or file does not exist
        if type(filename) != str:
            raise TypeError('`filename` must be of type `str`')
        if not os.path.exists(filename):
            if os.path.exists(filename + '.tif'):
                filename = filename + '.tif'
            else:
                raise FileNotFoundError(f'The file "{filename}" could not be'
                                        ' found.')
        
        self.filename = filename
        
        #load the image
        self.PIL_image = Image.open(filename)
        im = np.array(self.PIL_image)
        self.shape = np.shape(im)
        self.image = im[:self.shape[1]]
        self.dtype = self.image.dtype
    
    def get_metadata(self):
        """
        Loads metadata from the file.
        
        NOT IMPLEMENTED
        """
        #see https://github.com/ome/bioformats/blob/develop/components/formats-gpl/src/loci/formats/in/SISReader.java
        #and get_pixelsize for implementation details
        raise NotImplementedError('metadata for analySIS-tif not implemented,'
                                  'use the Bioformats module')
    
    
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
        #old tecnai 10 uses 33560 tag and a more complex format based on
        #Olympus analySIS software format. Only pixelsize is implemented atm
        #see https://github.com/ome/bioformats/blob/develop/components/formats-gpl/src/loci/formats/in/SISReader.java
        from struct import unpack
        try:
            with open(self.filename,'rb') as f:
                #find location of metadata from tag, then 64 bytes further the
                #start position of calibration metadata is written
                f.seek(self.PIL_image.tag[33560][0] + 64)
                metadataloc = int.from_bytes(f.read(4), 'little')
                #check loc with respect to length/size of file
                f.seek(0,2)
                flen = f.tell()
                if metadataloc+18 > flen:
                    raise EOFError()
                #go to metadataloc, skip first 10 bytes to get to pixelsize
                f.seek(metadataloc+10)
                unit = unpack('h',f.read(2))[0]#read short,=unit as power of 10
                if -12>=unit or unit>1:#check if value is reasonable
                    raise EOFError()
                pixelsize_x = unpack('d',f.read(8))[0]#read double, = pixelsize
                #pixelsize_y = unpack('d',f.read(8))[0]#same for y pixelsize
            
        except (KeyError, EOFError):
            raise KeyError('pixel size not encoded in file, are you sure this'
                           ' is the unmodified .tif file from the microscope?')
      
        #set the pixelsize to meter using the unit exponent/power of 10
        pixelsize_x *= 10**unit
        #pixelsize_y *= 10**unit
        
        
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
            from .utility import _convert_length
            pixelsize_x,unit = _convert_length(pixelsize_x, 'm', convert)
            
        #store and return
        self.pixelsize = pixelsize_x
        self.unit = unit
        return (pixelsize_x,unit)
        
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
        preprocess : callable, optional
            callable to pre-process the image before any other processing is 
            done, useful for e.g. smoothing. Must take and return a 
            numpy.ndarray containing the image data as only arguments, and must
            not change e.g. the pixel size or the scale bar may be incorrectly 
            sized. The default is None.
        crop : tuple or `None`, optional 
            range describing a area of the original image (before rescaling the
            resolution) to crop out for the export image. Can have two forms:
                
            - `((xmin,ymin),(xmax,ymax))`, with the integer pixel indices of 
            the top left and bottom right corners respectively.
                
            - `(xmin,ymin,w,h)` with the integer indices of the top left corner
            and the width and heigth of the cropped image in pixels (prior to 
            optional rescaling using `resolution`). When this format is used,
            it is possible to set the width and height in pixels (default) or 
            in data units via the `crop_unit` parameter.
            
            The default is `None` which takes the entire image.
        crop_unit : `'pixels'` or `'data'`, optional
            sets the unit in which the width and height in `crop` are 
            specified when using the (x,y,w,h) format, with `'pixels'` to give 
            the size in pixels or `'data'` to specify the size in the physical 
            unit used for the scalebar (after optional unit conversion via the 
            `convert` parameter). Note that the position of the top left corner
            is given in pixels. The `((xmin,ymin),(xmax,ymax))` format must be
            always given in pixels, and `crop_unit` is ignored if `crop` is 
            given in this format. The default is `'pixels'`.
        intensity_range : tuple or `None` or `'automatic'`
            tuple of `(lower,upper)` ranges for the (original) pixel values to 
            scale the brightness/contrast in the image to, or `'automatic'` to 
            autoscale the intensity to the 0.01th and 99.99th percentile of the 
            input image, or None for the min and max value in the original 
            image. The default is `None`.
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
        convert : str, one of [`'fm'`,`'pm'`,`'Å'` or `A`,`'nm'`,`'µm'` or `'um'`,`'mm'`,`'cm'`,`'dm'`,`'m'`]
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
            vertical offset for the baseline of the scale bar text from the top
            of the scale bar, in printer points. The default is 10.
        fontpad : int, optional
            minimum size in printer points of the space/padding between the 
            text and the bar and surrounding box. The default is 10.
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
            raise ValueError('overwriting original TEM file not reccomended, '+
                             'use a different filename for exporting.')
        
        #get image
        exportim = self.image.copy()
        
        #call main export_with_scalebar function with correct pixelsize etc
        from .utility import _export_with_scalebar
        _export_with_scalebar(exportim, pixelsize, unit, filename, **kwargs)


#make talos/tecnai alias for backwards compatibility
filterwarnings("default", category=DeprecationWarning,module='tecnai')
class tecnai(tia):
    """
    .. deprecated::
        The tecnai and Talos classes have been renamed to the `tia` class to 
        avoid confusion between data aquired using the older TIA and newer 
        Velox software from version 3.0.0 onwards. The old names are available 
        for backwards compatibility and should behave identically, but their 
        use is discouraged.
    
    
    Class of functions for TEM images from the tecnai microscopes operated with
    the TIA software
    
    See also
    --------
    `tia`
    """
    def __init__(self,*args,**kwargs):
        warn('The tecnai and Talos classes have been renamed to the `tia` '
             'class to avoid confusion between data aquired using the older '
             'TIA and newer Velox software from version 3.0.0 onwards. The old'
             ' names are available for backwards compatibility and should '
             'behave identically, but their use is discouraged.',
             DeprecationWarning,stacklevel=2)
        super().__init__(*args,**kwargs)

filterwarnings("default", category=DeprecationWarning,module='talos')
class talos(tia):
    """
    .. deprecated::
        The tecnai and Talos classes have been renamed to the `tia` class to 
        avoid confusion between data aquired using the older TIA and newer 
        Velox software from version 3.0.0 onwards. The old names are available 
        for backwards compatibility and should behave identically, but their 
        use is discouraged.
    
    Class of functions for TEM images from the Talos microscopes operated with
    the TIA software
    
    See also
    --------
    `tia`
    """
    def __init__(self,*args,**kwargs):
        warn('The tecnai and Talos classes have been renamed to the `tia` '
             'class to avoid confusion between data aquired using the older '
             'TIA and newer Velox software from version 3.0.0 onwards. The old'
             ' names are available for backwards compatibility and should '
             'behave identically, but their use is discouraged.',
             DeprecationWarning,stacklevel=2)
        super().__init__(*args,**kwargs)
