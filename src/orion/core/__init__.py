from pyutilib.component.core import *
from orion.api import IOrionPlugin

import os
import sys
from orion.core import comm

from orion.core.comm import xcbq
import xcb
from orion.core.comm import Server
from orion.core.comm import window
import gobject

class CoreError(Exception): pass

class Core ( SingletonPlugin ) :
    implements ( IOrionPlugin )
    
    def __init__(self):
        print 'core plugin running!'
        
    def init(self):
        displayName = os.environ.get("DISPLAY")
        if not displayName:
            raise CoreError("No DISPLAY set.")
        
        # prepare socket communication
        displayNum = displayName.partition(":")[2]
        if not "." in displayNum:
            displayName = displayName + ".0"
        self.sockname = comm.findSockfile(displayName, 'orion')
        self.conn = xcbq.Connection(displayName)

        # Find the modifier mask for the numlock key, if there is one:
        nc = self.conn.keysym_to_keycode(xcbq.keysyms["Num_Lock"])
        self.numlockMask = xcbq.ModMasks[self.conn.get_modifier(nc)]
        self.validMask = ~(self.numlockMask | xcbq.ModMasks["lock"])
        
        # Because we only do Xinerama multi-screening, we can assume that the first
        # screen's root is _the_ root.
        self.root = self.conn.default_screen.root
        self.root.set_attribute(
            eventmask = xcb.xproto.EventMask.StructureNotify |\
                        xcb.xproto.EventMask.SubstructureNotify |\
                        xcb.xproto.EventMask.SubstructureRedirect |\
                        xcb.xproto.EventMask.EnterWindow |\
                        xcb.xproto.EventMask.LeaveWindow
        )
        
        self.ignoreEvents = set([
            xcb.xproto.KeyReleaseEvent,
            xcb.xproto.ReparentNotifyEvent,
            xcb.xproto.CreateNotifyEvent,
            # DWM handles this to help "broken focusing windows".
            xcb.xproto.MapNotifyEvent,
            xcb.xproto.LeaveNotifyEvent,
            xcb.xproto.FocusOutEvent,
            xcb.xproto.FocusInEvent,
            xcb.xproto.NoExposureEvent
        ])
        
        self.screens = []
        self.currentScreen = None
        self._process_screens()
        self.currentScreen = self.screens[0]
        
        self.windowMap = {}
        
        self.conn.flush()
        self.conn.xsync()
        self._xpoll()
        
        self.server = Server(self.sockname, self)
        
        self.scan()
        
        ## run loop!
        self.loop()
    
    def loop(self):
        self.server.start()
        display_tag = gobject.io_add_watch(self.conn.conn.get_file_descriptor(), gobject.IO_IN, self._xpoll)
        try:
            context = gobject.main_context_default()
            while True:
                if context.iteration(True):
                    # this seems to be crucial part
                    self.conn.flush()
                #if self._exit:
                #    break
        finally:
            gobject.source_remove(display_tag)
    
    def _xpoll(self, conn=None, cond=None):
        while True:
            try:
                e = self.conn.conn.poll_for_event()
                if not e:
                    break
                # This should be done in xpyb
                # client mesages start at 128
                if e.response_type >= 128:
                    e = xcb.xproto.ClientMessageEvent(e)

                ename = e.__class__.__name__

                if ename.endswith("Event"):
                    ename = ename[:-5]
                if self.debug:
                    if ename != self._prev:
                        print >> sys.stderr, '\n', ename,
                        self._prev = ename
                        self._prev_count = 0
                    else:
                        self._prev_count += 1
                        # only print every 10th
                        if self._prev_count % 20 == 0:
                            print >> sys.stderr, '.',
                if not e.__class__ in self.ignoreEvents:
                    for h in self.get_target_chain(ename, e):
                        self.log.add("Handling: %s"%ename)
                        r = h(e)
                        if not r:
                            break
            except Exception, v:
                raise v
                self.errorHandler(v)
                if self._exit:
                    return False
                continue
        return True
    
    def scan(self):
        _, _, children = self.root.query_tree()
        print len(children)
        for item in children:
            try:
                attrs = item.get_attributes()
                state = item.get_wm_state()
            except (xcb.xproto.BadWindow, xcb.xproto.BadAccess):
                continue

            if attrs and attrs.map_state == xcb.xproto.MapState.Unmapped:
                continue
            if state and state[0] == window.WithdrawnState:
                continue
            print item
            self.manage(item)
    
    def manage(self, w):
        try:
            attrs = w.get_attributes()
            internal = w.get_property("QTILE_INTERNAL")
        except (xcb.xproto.BadWindow, xcb.xproto.BadAccess):
            return
        if attrs and attrs.override_redirect:
            return

        if not w.wid in self.windowMap:
            if internal:
                try:
                    c = window.Internal(w, self)
                except (xcb.xproto.BadWindow, xcb.xproto.BadAccess):
                    return
                self.windowMap[w.wid] = c
            else:
                try:
                    c = window.Window(w, self)
                except (xcb.xproto.BadWindow, xcb.xproto.BadAccess):
                    return
                # Window may be defunct because it's been declared static in hook.
                if c.defunct:
                    return
                self.windowMap[w.wid] = c
                # Window may have been bound to a group in the hook.
            return c
        else:
            return self.windowMap[w.wid]

    def _process_screens(self):
        for i, s in enumerate(self.conn.pseudoscreens):
            scr = Screen()
            if not self.currentScreen:
                self.currentScreen = scr
            scr._configure(
                self,
                i,
                s.x,
                s.y,
                s.width,
                s.height,
            )
            self.screens.append(scr)

        if not self.screens:
            if self.config.screens:
                s = self.config.screens[0]
            else:
                s = Screen()
            self.currentScreen = s
            s._configure(
                self,
                0, 0, 0,
                self.conn.default_screen.width_in_pixels,
                self.conn.default_screen.height_in_pixels,
                self.groups[0],
            )
            self.screens.append(s)


class ScreenRect(object):

    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def __repr__(self):
        return '<%s %d,%d %d,%d>' % (self.__class__.__name__,
            self.x, self.y, self.width, self.height)

    def hsplit(self, columnwidth):
        assert columnwidth > 0
        assert columnwidth < self.width
        return (self.__class__(self.x, self.y, columnwidth, self.height),
                self.__class__(self.x+columnwidth, self.y,
                               self.width - columnwidth, self.height))

    def vsplit(self, rowheight):
        assert rowheight > 0
        assert rowheight < self.height
        return (self.__class__(self.x, self.y, self.width, rowheight),
                self.__class__(self.x, self.y + rowheight,
                               self.width, self.height - rowheight))

# extends command.CommandObject
class Screen(object):
    """
        A physical screen, and its associated paraphernalia.
    """
    group = None
    def __init__(self, top=None, bottom=None, left=None, right=None,
                 x=None, y=None, width=None, height=None):
        """
            - top, bottom, left, right: Instances of bar objects, or None.

            Note that bar.Bar objects can only be placed at the top or the
            bottom of the screen (bar.Gap objects can be placed anywhere).

            x,y,width and height aren't specified usually unless you are
            using 'fake screens'.
        """
        self.top, self.bottom = top, bottom
        self.left, self.right = left, right
        self.qtile = None
        self.index = None
        self.x = x # x position of upper left corner can be > 0
                      # if one screen is "right" of the other
        self.y = y
        self.width = width
        self.height = height


    def _configure(self, qtile, index, x, y, width, height):
        self.qtile = qtile
        self.index, self.x, self.y = index, x, y,
        self.width, self.height = width, height
        for i in self.gaps:
            i._configure(qtile, self)

    @property
    def gaps(self):
        lst = []
        for i in [self.top, self.bottom, self.left, self.right]:
            if i:
                lst.append(i)
        return lst

    @property
    def dx(self):
        return self.x + self.left.size if self.left else self.x

    @property
    def dy(self):
        return self.y + self.top.size if self.top else self.y

    @property
    def dwidth(self):
        val = self.width
        if self.left:
            val -= self.left.size
        if self.right:
            val -= self.right.size
        return val

    @property
    def dheight(self):
        val = self.height
        if self.top:
            val -= self.top.size
        if self.bottom:
            val -= self.bottom.size
        return val

    def get_rect(self):
        return ScreenRect(self.dx, self.dy, self.dwidth, self.dheight)

    def setGroup(self, new_group):
        """
        Put group on this screen
        """
        if new_group.screen == self:
            return
        elif new_group.screen:
            # g1 <-> s1 (self)
            # g2 (new_group)<-> s2 to
            # g1 <-> s2
            # g2 <-> s1
            g1 = self.group
            s1 = self
            g2 = new_group
            s2 = new_group.screen

            s2.group = g1
            g1._setScreen(s2)
            s1.group = g2
            g2._setScreen(s1)
        else:
            if self.group is not None:
                self.group._setScreen(None)
            self.group = new_group
            new_group._setScreen(self)
        #hook.fire("setgroup")
        #hook.fire("focus_change")

    def _items(self, name):
        if name == "layout":
            return True, range(len(self.group.layouts))
        elif name == "window":
            return True, [i.window.wid for i in self.group.windows]
        elif name == "bar":
            return False, [x.position for x in self.gaps]

    def _select(self, name, sel):
        if name == "layout":
            if sel is None:
                return self.group.layout
            else:
                return utils.lget(self.group.layouts, sel)
        elif name == "window":
            if sel is None:
                return self.group.currentWindow
            else:
                for i in self.group.windows:
                    if i.window.wid == sel:
                        return i
        elif name == "bar":
            return getattr(self, sel)

    def resize(self, x=None, y=None, w=None, h=None):
        x = x or self.x
        y = y or self.y
        w = w or self.width
        h = h or self.height
        self._configure(self.qtile, self.index, x, y, w, h, self.group)
        for bar in [self.top, self.bottom, self.left, self.right]:
            if bar:
                bar.draw()
        self.group.layoutAll()

    def cmd_info(self):
        """
            Returns a dictionary of info for this screen.
        """
        return dict(
            index=self.index,
            width=self.width,
            height=self.height,
            x = self.x,
            y = self.y
        )

    def cmd_resize(self, x=None, y=None, w=None, h=None):
        """
            Resize the screen.
        """
        self.resize(x, y, w, h)