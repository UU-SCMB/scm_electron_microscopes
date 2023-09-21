__version__ = '3.2.5'

from .tem import tia,sis,velox,velox_image,velox_edx,tecnai,talos
from .sem import helios,phenom,xl30sfeg,ZeissSEM
from .utility import util

#make visible for 'from scm_electron_microscopes import *'
__all__ = [
    'tecnai',
    'talos',
    'tia',
    'sis',
    'velox',
    'velox_image',
    'velox_edx',
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
