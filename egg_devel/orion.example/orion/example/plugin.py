from pyutilib.component.core import *
from orion.api import IOrionPlugin

class PluginExample ( SingletonPlugin ) :
    implements ( IOrionPlugin )
    
    def __init__(self):
        print 'example plugin running!'