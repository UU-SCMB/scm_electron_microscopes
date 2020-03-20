# scm_electron_microscopes
Set of functions for dealing with data from the electron microscopes at Utrecht University

**[The documentation can be found here](https://maartenbransen.github.io/scm_electron_microscopes/)**

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

## Usage

#### Tecnai 12, Tecnai 20, Tecnai 20feg, Talos
For these microscopes use the `tecnai` class, e.g. `from scm_electron_microscopes import tecnai`

#### Helios
For the Helios SCM use the `helios` class

#### Phenom
For any of the Phenom SEMs use the `phenom` class

#### XL30sFEG
For this microscope use the `xl30sfeg` class

#### Utility functions
Some utility functions for e.g. plotting a histogram are included in the `util` class
