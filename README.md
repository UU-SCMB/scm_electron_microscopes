# scm_electron_microscopes
Set of functions for dealing with data from the electron microscopes at Utrecht University

**[The full API documentation can be found here](https://maartenbransen.github.io/scm_electron_microscopes/)**

## Info
- Created by: Maarten Bransen
- Email: m.bransen@uu.nl

## Installation instructions
Download the `scm_electron_microscopes` folder and place it in your `site-packages` location of your Anaconda installation. If you are unsure where this is located you can find the path of any already installed package, e.g. using numpy:
```
import numpy
print(numpy.__file__)
```
which may print something like
```
'<current user>\\AppData\\Local\\Continuum\\anaconda3\\lib\\site-packages\\numpy\\__init__.py'
```
Alternatively, you can make sure that the folder is located in your current working directory, or any other directory which is added to the `PYTHONPATH` variable of your python environment.

To use automatic scale bar calibration for the Tecnai and Talos microscopes, the [tesseract optical character recognition](https://github.com/tesseract-ocr/tesseract) tool is used which must be installed separately, installation files can be found [here](https://tesseract-ocr.github.io/tessdoc/Home.html). This is interfaced through the `pytesseract` package which can be installed normally using e.g. conda. It may be necessary to point it towards your tesseract installation by changing the `pytesseract.pytesseract.tesseract_cmd` variable to the correct path, something like `tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'`.

## Usage

### Tecnai 12, Tecnai 20, Tecnai 20feg, Talos120, Talos200
For these microscopes use the `tecnai` or `talos` class (these are identical, the alias `talos` is just provided for convenience), and create a class instance using the filename of the TEM image. This automatically loads the image, which is available as numpy.array as the `image` attribute:
```
from scm_electron_microscopes import tecnai

em_data = tecnai('myimage.tif')
image = em_data.image
```
Note that this is only the image data, with the scalebar stripped off. The imagedata for the scale bar is available through the `scalebar` attribute, but more likely you are interested in the pixel size which can be determined semi or fully automatic:
```
pixelsize,unit = em_data.get_pixelsize()
```
for fully automatic calibration of the scalebar, pytesseract and the tesseract-OCR must be installed, if these are not found the function switches to semi-automatic mode where the user is asked to give the size and unit written next to the scalebar. Other information about the microscope is read from the file and can be printed with `tecnai.print_metadata()`. Files can be exported with a nicer and customizable scalebar using the `tecnai.export_with_scalebar()` function.

### Helios
For the Helios SEM use the `helios` class, which unlike the `tecnai` and `talos` classes does not load the image into memory by default, such that it is possible to quickly read out metadata of e.g. a slice-and-view series without having to load all the image data. Image data is available through the `load_image` function:
```
from scm_electron_microscopes import helios

em_data = helios('myimage.tif')
image = em_data.load_image()
```

Pixel sizes written in the metadata and available as a shortcut through a function:
```
(pixelsize_x,pixelsize_y),unit  = em_data.get_pixelsize()
```

Other information about the microscope is read from the file and can be printed in a human-readable format with `helios.print_metadata()` or parsed directly through `helios.load_metadata()`. Files can be exported with a nicer and customizable scalebar using the `helios.export_with_scalebar()` function.

### Phenom
For any of the Phenom SEMs use the `phenom` class, which works similar as described above for the `helios` class.

### XL30sFEG
This microscope is no longer around, but for older data you can use the `xl30sfeg` class

### Utility functions
Some utility functions for e.g. plotting a histogram are included in the `util` class
