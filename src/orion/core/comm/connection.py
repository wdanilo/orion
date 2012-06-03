import struct
import xcb.xproto, xcb.xinerama, xcb.randr, xcb.xcb
from xcb.xproto import CW, WindowClass, EventMask
from orion import utils
from orion import  xkeysyms

from orion.core.window import proto
from orion.core.window import icccm

from orion.core.screen.extensions import Xinerama, RandR

from orion.xcbq import Window
from orion.xcbq import AtomCache

class _Wrapper:
    def __init__(self, wrapped):
        self.wrapped = wrapped

    def __getattr__(self, x):
        return getattr(self.wrapped, x)


class XScreen(_Wrapper):
    """
        This represents an actual X screen.
    """
    def __init__(self, conn, screen):
        _Wrapper.__init__(self, screen)
        self.default_colormap = Colormap(conn, screen.default_colormap)
        self.root = Window(conn, self.root)



class Colormap:
    def __init__(self, conn, cid):
        self.conn, self.cid = conn, cid

    def alloc_color(self, color):
        """
            Flexible color allocation.
        """
        if color.startswith("#"):
            if len(color) != 7:
                raise ValueError("Invalid color: %s"%color)
            def x8to16(i):
                return 0xffff * (i&0xff)/0xff
            r = x8to16(int(color[1] + color[2], 16))
            g = x8to16(int(color[3] + color[4], 16))
            b = x8to16(int(color[5] + color[6], 16))
            return self.conn.conn.core.AllocColor(self.cid, r, g, b).reply()
        else:
            return self.conn.conn.core.AllocNamedColor(self.cid, len(color), color).reply()

class Connection:
    _extmap = {
        "xinerama": Xinerama,
        "randr": RandR,
    }
    def __init__(self, display):
        self.conn = xcb.xcb.connect(display=display)
        self.setup = self.conn.get_setup()
        
        # collect available extensions
        self.__extensions = []
        for name in self.conn.core.ListExtensions().reply().names:
            self.__extensions.append(utils.chrArr(name.name).lower())
            
        # collect screens
        self.screens = [XScreen(self, i) for i in self.setup.roots]
        
        # check for xinerama and randr screens        
        self.pseudoscreens = []
        extension = None
        if "xinerama" in self.extensions:
            extension = Xinerama(self)
        elif "randr" in self.extensions:
            extension = RandR(self)
        if extension:
            self.pseudoscreens = extension.query_screens()

        self.default_screen = self.screens[self.conn.pref_screen]
        
        
        self.atoms = AtomCache(self)

        # compute keycodes
        self.code_to_syms     = None
        self.first_sym_to_code = None
        self.refresh_keymap()

        # get modifier mapping
        self.modmap = None
        self.refresh_modmap()

    def refresh_keymap(self, first=None, count=None):
        if first is None:
            first = self.setup.min_keycode
            count = self.setup.max_keycode - self.setup.min_keycode + 1
        q = self.conn.core.GetKeyboardMapping(first, count).reply()
        
        self.code_to_syms = {}
        l = []
        for i, v in enumerate(q.keysyms):
            if not i%q.keysyms_per_keycode:
                if l:
                    self.code_to_syms[(i/q.keysyms_per_keycode) + first - 1] = l
                l = []
                l.append(v)
            else:
                l.append(v)
        assert len(l) == q.keysyms_per_keycode
        self.code_to_syms[first + count - 1] = l

        first_sym_to_code = {}
        for k, s in self.code_to_syms.items():
            first_sym_to_code[s[0]] = k

        self.first_sym_to_code = first_sym_to_code

    def refresh_modmap(self):
        q = self.conn.core.GetModifierMapping().reply()
        modmap = {}
        mods = proto.ModMasks.keys()
        for i, k in enumerate(q.keycodes):
            l = modmap.setdefault(mods[i/q.keycodes_per_modifier], [])
            l.append(k)
        self.modmap = modmap

    def get_modifier(self, keycode):
        """
            Return the modifier matching keycode.
        """
        for n, l in self.modmap.items():
            if keycode in l:
                return n
        return None

    def keysym_to_keycode(self, keysym):
        return self.first_sym_to_code.get(keysym, 0)

    def keycode_to_keysym(self, keycode, modifier):
        if keycode >= len(self.code_to_syms) or modifier >= len(self.code_to_syms[keycode]):
            return 0
        return self.code_to_syms[keycode][modifier]

    def create_window(self, x, y, width, height):
        wid = self.conn.generate_id()
        q = self.conn.core.CreateWindow(
                self.default_screen.root_depth,
                wid,
                self.default_screen.root.wid,
                x, y, width, height, 0,
                WindowClass.InputOutput,
                self.default_screen.root_visual,
                CW.BackPixel|CW.EventMask,
                [
                    self.default_screen.black_pixel,
                    EventMask.StructureNotify|EventMask.Exposure
                ]
        )
        return Window(self, wid)

    def flush(self):
        return self.conn.flush()

    def xsync(self):
        # The idea here is that pushing an innocuous request through
        # the queue and waiting for a response "syncs" the connection, since
        # requests are serviced in order.
        self.conn.core.GetInputFocus().reply()

    def grab_server(self):
        return self.conn.core.GrabServer()

    def get_setup(self):
        return self.conn.get_setup()

    def open_font(self, name):
        fid = self.conn.generate_id()
        self.conn.core.OpenFont(fid, len(name), name)
        return Font(self, fid)

    @property
    def extensions(self):
        return self.__extensions