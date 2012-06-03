import xcb
from orion.core.screen.screen import Screen

class RandR(object):
    def __init__(self, conn):
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