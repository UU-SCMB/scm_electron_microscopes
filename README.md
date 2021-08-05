# scm_electron_microscopes
Set of functions for dealing with data from the electron microscopes at Utrecht University

**[The full API documentation can be found here](https://maartenbransen.github.io/scm_electron_microscopes/)**

## Info
- Created by: Maarten Bransen
- Email: m.bransen@uu.nl
- Version: 2.0.2

## Installation

### PIP
This package can be installed directly from GitHub using pip:
```
pip install git+https://github.com/MaartenBransen/scm_electron_microscopes
```
### Anaconda
When using the Anaconda distribution, it is safer to run the conda version of pip as follows:
```
conda install pip
conda install git
pip install git+https://github.com/MaartenBransen/scm_electron_microscopes
```
### Updating
To update to the most recent version, use `pip install` with the `--upgrade` flag set:
```
pip install --upgrade git+https://github.com/MaartenBransen/scm_electron_microscopes
```

## Usage
### Tecnai 12, Tecnai 20, Tecnai 20feg, Talos120, Talos200

**Note that since version 2.0.0 Pytesseract is no longer required as dependency**


For these microscopes use the [tecnai](https://maartenbransen.github.io/scm_electron_microscopes/#scm_electron_microscopes.tecnai) or [talos](https://maartenbransen.github.io/scm_electron_microscopes/#scm_electron_microscopes.talos) class (these are identical, the alias `talos` is just provided for convenience), and create a class instance using the filename of the TEM image. This automatically loads the image, which is available as numpy.array as the `image` attribute:
```
from scm_electron_microscopes import tecnai
import matplotlib.pyplot as plt

em_data = tecnai('myimage.tif')
image = em_data.image

plt.figure()
plt.imshow(image,cmap='Greys_r')
plt.axis('off')
plt.show()
```
Note that this is only the image data, with the scalebar stripped off. The imagedata for the scale bar is available through the `scalebar` attribute, but more likely you are interested in the pixel size which can be determined semi or fully automatically using `tecnai.get_pixelsize()`:
```
pixelsize,unit = em_data.get_pixelsize()
```
Other information about the microscope is read from the file and can be printed with `tecnai.print_metadata()`. Files can be exported with a nicer and customizable scalebar using the `tecnai.export_with_scalebar()` function.

### Helios
For the Helios SEM use the [helios](https://maartenbransen.github.io/scm_electron_microscopes/#scm_electron_microscopes.helios) class, which unlike the `tecnai` and `talos` classes does not load the image into memory by default, such that it is possible to quickly read out metadata of e.g. a slice-and-view series without having to load all the image data. Image data is available through the `load_image()` function:
```
from scm_electron_microscopes import helios

em_data = helios('myimage.tif')
image = em_data.get_image()
```

Pixel sizes written in the metadata and available as a shortcut through a function:
```
(pixelsize_x,pixelsize_y),unit  = em_data.get_pixelsize()
```

Other information about the microscope is read from the file and can be printed in a human-readable format with `helios.print_metadata()` or parsed directly through `helios.load_metadata()`. Files can be exported with a nicer and customizable scalebar using the `helios.export_with_scalebar()` function.

### Phenom
For any of the Phenom SEMs use the [phenom](https://maartenbransen.github.io/scm_electron_microscopes/#scm_electron_microscopes.phenom) class, which works similar as described above for the `helios` class.

### XL30sFEG
This microscope is no longer around, but for older data you can use the `xl30sfeg` class

### Utility functions
Some utility functions for e.g. plotting a histogram are included in the [util](https://maartenbransen.github.io/scm_electron_microscopes/#scm_electron_microscopes.util) class


## Changelog

### Version 2.0.0
Note that this version has some backwards incompatible changes:
- `load_image` functions have been renamed to `get_image`
- `load_metadata` functions have been renamed to `get_metadata`
- `tecnai.get_pixelsize` no longer uses text recognition to read the scale bar. This is faster and removes Pytesseract and the Tesseract OCR as dependencies, but yields slightly different (and more accurate) values. The old scaling method is available through `get_pixelsize_legacy`.
- all `get_metadata` functions now return an xml.etree.Elementtree object by default, rather than a dictionary which was used for some classes.
