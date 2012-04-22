import xcb
import xcb.xinerama
import xcb.randr
from orion.core import keyboard
from orion.core.window import Window
from orion.core.screen import Screen

class Extension(object):
    pass

class Xinerama(Extension):
    def __init__(self, conn):
        super(Xinerama, self).__init__()
        self.ext = conn.conn(xcb.xinerama.key)

    def query_screens(self):
        r = self.ext.QueryScreens().reply()
        return r.screen_info


class RandR(Extension):
    def __init__(self, conn):
        super(RandR, self).__init__()
        self.ext = conn.conn(xcb.randr.key)

    def query_crtcs(self, root):
        l = []
        for i in self.ext.GetScreenResources(root).reply().crtcs:
            info = self.ext.GetCrtcInfo(i, xcb.CurrentTime).reply()
            d = dict(
                x = info.x,
                y = info.y,
                width = info.width,
                height = info.height
            )
            l.append(d)
        return l

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
        #self.default_colormap = Colormap(conn, screen.default_colormap)
        self.root = Window(conn, self.root)


class MetaScreenx:
    """
        This may be a Xinerama screen or a RandR CRTC, both of which are
        rectagular sections of an actual Screen.
    """
    def __init__(self, conn, x, y, width, height):
        self.conn = conn
        self.x, self.y, self.width, self.height = x, y, width, height


WindowTypes = {
    '_NET_WM_WINDOW_TYPE_DESKTOP': "desktop",
    '_NET_WM_WINDOW_TYPE_DOCK': "dock",
    '_NET_WM_WINDOW_TYPE_TOOLBAR': "toolbar",
    '_NET_WM_WINDOW_TYPE_MENU': "menu",
    '_NET_WM_WINDOW_TYPE_UTILITY': "utility",
    '_NET_WM_WINDOW_TYPE_SPLASH': "splash",
    '_NET_WM_WINDOW_TYPE_DIALOG': "dialog",
    '_NET_WM_WINDOW_TYPE_DROPDOWN_MENU': "dropdown",
    '_NET_WM_WINDOW_TYPE_POPUP_MENU': "menu",
    '_NET_WM_WINDOW_TYPE_TOOLTIP': "tooltip",
    '_NET_WM_WINDOW_TYPE_NOTIFICATION': "notification",
    '_NET_WM_WINDOW_TYPE_COMBO': "combo",
    '_NET_WM_WINDOW_TYPE_DND': "dnd",
    '_NET_WM_WINDOW_TYPE_NORMAL': "normal",
}


class AtomCache:
    def __init__(self, conn):
        self.conn = conn
        self.atoms = {}
        self.reverse = {}

        # We can change the pre-loads not to wait for a return
        for name in WindowTypes.keys():
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
    
class Connection:
    def __init__(self, display):
        self.extensions     = []
        self.codeToSyms     = {}
        self.firstSymToCode = None
        self.modmap         = None
        
        self.conn     = xcb.connect(display=display)
        self.atoms = AtomCache(self)
        self.setup    = self.conn.get_setup()
        extensionList = self.listExtensions()
        self.xscreens = [XScreen(self, i) for i in self.setup.roots]
        self.screens = []
        if "xinerama" in extensionList:
            extension = Xinerama(self)
            for num, screenInfo in enumerate(extension.query_screens()):
                scr = Screen(
                    screenInfo.x_org,
                    screenInfo.y_org,
                    screenInfo.width,
                    screenInfo.height,
                )
                self.screens.append(scr)
        elif "randr" in extensionList:
            extension = RandR(self)
            for i in extension.query_crtcs(self.screens[0].root.wid):
                scr = Screen(
                    i["x"],
                    i["y"],
                    i["width"],
                    i["height"],
                )
                self.screens.append(scr)

        self.defaultScreen = self.xscreens[self.conn.pref_screen]
        self.refreshKeymap()
        self.refreshModmap()
        
    def refreshKeymap(self, first=None, count=None):
        if first is None:
            first = self.setup.min_keycode
            count = self.setup.max_keycode - self.setup.min_keycode + 1
        q = self.conn.core.GetKeyboardMapping(first, count).reply()

        l = []
        for i, v in enumerate(q.keysyms):
            if not i%q.keysyms_per_keycode:
                if l:
                    self.codeToSyms[(i/q.keysyms_per_keycode) + first - 1] = l
                l = []
                l.append(v)
            else:
                l.append(v)
        assert len(l) == q.keysyms_per_keycode
        self.codeToSyms[first + count - 1] = l

        firstSymToCode = {}
        for k, s in self.codeToSyms.items():
            firstSymToCode[s[0]] = k

        self.firstSymToCode = firstSymToCode

    def refreshModmap(self):
        q = self.conn.core.GetModifierMapping().reply()
        modmap = {}
        for i, k in enumerate(q.keycodes):
            l = modmap.setdefault(keyboard.modMapOrder[i/q.keycodes_per_modifier], [])
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
        return self.firstSymToCode.get(keysym, 0)

    def keycode_to_keysym(self, keycode, modifier):
        if keycode >= len(self.codeToSyms) or modifier >= len(self.codeToSyms[keycode]):
            return 0
        return self.codeToSyms[keycode][modifier]

    def create_window(self, x, y, width, height):
        wid = self.conn.generate_id()
        q = self.conn.core.CreateWindow(
                self.defaultScreen.root_depth,
                wid,
                self.defaultScreen.root.wid,
                x, y, width, height, 0,
                WindowClass.InputOutput,
                self.defaultScreen.root_visual,
                CW.BackPixel|CW.EventMask,
                [
                    self.defaultScreen.black_pixel,
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

    def listExtensions(self):
        def toStr(s):
            return "".join([chr(i) for i in s.name])
        return [toStr(i).lower() for i in self.conn.core.ListExtensions().reply().names]