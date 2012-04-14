from pyutilib.component.core import *
from orion.api import IOrionPlugin

class Core ( SingletonPlugin ) :
    implements ( IOrionPlugin )
    
    def __init__(self):
        print 'core plugin running!'