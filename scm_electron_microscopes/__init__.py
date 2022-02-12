__version__ = '3.0.1'

from .tem import tia,velox,velox_image,tecnai,talos
from .sem import helios,phenom,xl30sfeg,ZeissSEM
from .utility import util

#make visible for 'from scm_electron_microscopes import *'
__all__ = [
    'tecnai',
    'talos',
    'velox',
    'velox_image',
    'helios',
    'phenom',
    'xl30sfeg',
    'ZeissSEM',
    'util'
]

#add submodules to pdoc ignore list for generated documentation
__pdoc__ = {
    'tem' : False,
    'sem' : False,
    'utility' : False,
}
