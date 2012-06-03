import xcb.xinerama
from orion.core.screen.screen import Screen


class Xinerama(object):
    def __init__(self, conn):
        self.ext = conn.conn(xcb.xinerama.key)

    def query_screens(self):
        info = self.ext.QueryScreens().reply().screen_info
        return [Screen(s.x_org, s.y_org, s.width, s.height) for s in info]