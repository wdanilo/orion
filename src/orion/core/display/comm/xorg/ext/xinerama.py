import xcb.xinerama
from orion.core.screen.screen import Screen
from pyutilib.component.core import implements, SingletonPlugin
from api import IXorgExtension

class Xinerama(SingletonPlugin):
    implements (IXorgExtension)
    
    def __init__(self):
        self.name = 'xinerama'
        
    def init(self, conn):
        self.ext = conn.conn(xcb.xinerama.key)

    def query_screens(self):
        info = self.ext.QueryScreens().reply().screen_info
        return [Screen(s.x_org, s.y_org, s.width, s.height) for s in info]