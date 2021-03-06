import xcb
from orion.wm.screen.screen import Screen
from pyutilib.component.core import implements, SingletonPlugin
from api import IXorgExtension

class RandR(SingletonPlugin):
    implements (IXorgExtension)
    
    def __init__(self):
        self.name = 'randr'
        
    def init(self, conn):
        self.ext = conn.conn(xcb.randr.key)
        self.__conn = conn

    def query_screens(self):
        screens = self.query_crtcs(self.__conn.screens[0].root.wid)
        return screens
    
    def query_crtcs(self, root):
        l = []
        for i in self.ext.GetScreenResources(root).reply().crtcs:
            info = self.ext.GetCrtcInfo(i, xcb.xcb.CurrentTime).reply()
            l.append(Screen(info.x_org, info.y_org, info.width, info.height))
        return l