from .tem import tecnai
from .sem import helios,phenom,xl30sfeg
from .utility import util

#make talos alias for tecnai/talos class
talos = tecnai
talos.__name__ = 'talos'

#make visible for 'from stackscroller import *'
__all__ = [
    'tecnai',
    'talos',
    'helios',
    'phenom',
    'xl30sfeg',
    'util'
]

#add submodules to pdoc ignore list for generated documentation
__pdoc__ = {
    'tem' : False,
    'sem' : False,
    'utility' : False,
}