__version__ = '2.0.2'

from .tem import tecnai,velox
from .sem import helios,phenom,xl30sfeg,ZeissSEM
from .utility import util

#make talos alias for identical tecnai/talos class
talos = type('talos', tecnai.__bases__, dict(tecnai.__dict__))
talos.__doc__ = 'Alias of `tecnai` class\n'+talos.__doc__

#make visible for 'from stackscroller import *'
__all__ = [
    'tecnai',
    'talos',
    'velox',
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
