"""
    A minimal EWMH-aware OO layer over xpyb. This is NOT intended to be
    complete - it only implements the subset of functionalty needed by qtile.
"""
import struct
import xcb.xproto, xcb.xinerama, xcb.randr, xcb.xcb
from xcb.xproto import CW, WindowClass, EventMask
import utils, xkeysyms

from orion.core.window import proto
from orion.core.window import icccm

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




class AtomCache:
    def __init__(self, conn):
        self.conn = conn
        self.atoms = {}
        self.reverse = {}

        # We can change the pre-loads not to wait for a return
        for name in proto.WindowTypes.keys():
            self.insert(name=name)

        for i in dir(xcb.xproto.Atom):
            if not i.startswith("_"):
                self.insert(name=i, atom=getattr(xcb.xproto.Atom, i))

    def insert(self, name = None, atom = None):
        assert name or atom
        if atom is None:
            c = self.conn.conn.core.InternAtom(False, len(name), name)
            atom = c.reply().atom
        if name is None:
            c = self.conn.conn.core.GetAtomName(atom)
            name = str(c.reply().name.buf())
        self.atoms[name] = atom
        self.reverse[atom] = name

    def get_name(self, atom):
        if atom not in self.reverse:
            self.insert(atom=atom)
        return self.reverse[atom]

    def __getitem__(self, key):
        if key not in self.atoms:
            self.insert(name=key)
        return self.atoms[key]





class GC:
    def __init__(self, conn, gid):
        self.conn, self.gid = conn, gid

    def change(self, **kwargs):
        mask, values = GCMasks(**kwargs)
        self.conn.conn.core.ChangeGC(self.gid, mask, values)






from orion.core.window import proto

import sys, struct, contextlib
#import xcb.xcb
from xcb.xproto import EventMask, StackMode, SetMode
import xcb.xproto
from orion import utils
#import command
from orion import hook

from orion.utils import flagEnum, enum

from orion.core.window.icccm import wmState
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



