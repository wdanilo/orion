"""
    A minimal EWMH-aware OO layer over xpyb. This is NOT intended to be
    complete - it only implements the subset of functionalty needed by qtile.
"""
import struct
import xcb.xproto, xcb.xinerama, xcb.randr, xcb.xcb
from xcb.xproto import CW, WindowClass, EventMask
import utils
from orion.wm.keyboard import xkeysyms

from orion.wm.window import proto
from orion.wm.window import icccm

# hack xcb.xproto for negative numbers
def ConfigureWindow(self, window, value_mask, value_list):
    import cStringIO
    from struct import pack
    from array import array
    buf = cStringIO.StringIO()
    buf.write(pack('xx2xIH2x', window, value_mask))
    buf.write(str(buffer(array('i', value_list))))
    return self.send_request(xcb.Request(buf.getvalue(), 12, True, False),
                                 xcb.VoidCookie())
xcb.xproto.xprotoExtension.ConfigureWindow = ConfigureWindow

keysyms = xkeysyms.keysyms


def toStr(s):
    return "".join([chr(i) for i in s.name])










class GC:
    def __init__(self, conn, gid):
        self.conn, self.gid = conn, gid

    def change(self, **kwargs):
        mask, values = GCMasks(**kwargs)
        self.conn.conn.core.ChangeGC(self.gid, mask, values)






from orion.wm.window import proto

import sys, struct, contextlib
#import xcb.xcb
from xcb.xproto import EventMask, StackMode, SetMode
import xcb.xproto
from orion import utils
#import command
from orion import hook

from orion.utils import flagEnum, enum

from orion.wm.window.icccm import wmState
# float states



class Font:
    def __init__(self, conn, fid):
        self.conn, self.fid = conn, fid

    @property
    def _maskvalue(self):
        return self.fid

    def text_extents(self, s):
        s = s + "aaa"
        print s
        x = self.conn.conn.core.QueryTextExtents(self.fid, len(s), s).reply()
        print x
        return x



