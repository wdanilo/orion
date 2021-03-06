import atexit, sys, os, traceback
import contextlib
import gobject
#import xcbq
import xcb.xproto, xcb.xinerama
import xcb
from xcb.xproto import EventMask
from orion import utils, hook
from orion.wm.window import window
from orion.wm.screen import Screen
from orion.wm.window.window import Window
from orion.signals import SignalGroup
from pyutilib.component.core import ExtensionPoint
from orion.comm.api import IDisplayServerCommunicator
from pyutilib.component.core import implements, SingletonPlugin
from orion.wm.api import IWindowManager
#import command

import logging
logger = logging.getLogger(__name__)


import orion



class QtileError(Exception): pass



# command.CommandObject
class Group(object):
    """
        A group is a container for a bunch of windows, analogous to workspaces
        in other window managers. Each client window managed by the window
        manager belongs to exactly one group.
    """
    def __init__(self, name, layout=None):
        self.name = name
        self.customLayout = layout  # will be set on _configure
        self.windows = set()
        self.qtile = None
        self.layouts = []
        self.floating_layout = None
        self.currentWindow = None
        self.screen = None
        self.currentLayout = None

    def _configure(self, layouts, floating_layout, qtile):
        self.screen = None
        self.currentLayout = 0
        self.currentWindow = None
        self.windows = set()
        self.qtile = qtile
        self.layouts = [i.clone(self) for i in layouts]
        self.floating_layout = floating_layout.clone(self)
        if self.customLayout is not None:
            self.layout = self.customLayout
            self.customLayout = None

    @property
    def layout(self):
        return self.layouts[self.currentLayout]

    @layout.setter
    def layout(self, layout):
        """
            "layout" is a string with matching the name of a Layout object.
        """
        for index, obj in enumerate(self.layouts):
            if obj.name == layout:
                self.currentLayout = index
                hook.fire("layout_change", self.layouts[self.currentLayout])
                self.layoutAll()
                return
        raise ValueError("No such layout: %s"%layout)

    def nextLayout(self):
        self.layout.hide()
        self.currentLayout = (self.currentLayout + 1)%(len(self.layouts))
        hook.fire("layout_change", self.layouts[self.currentLayout])
        self.layoutAll()
        screen = self.screen.get_rect()
        self.layout.show(screen)

    def prevLayout(self):
        self.layout.hide()
        self.currentLayout = (self.currentLayout - 1)%(len(self.layouts))
        hook.fire("layout_change", self.layouts[self.currentLayout])
        self.layoutAll()
        screen = self.screen.get_rect()
        self.layout.show(screen)

    def layoutAll(self, warp=False):
        """
        Layout the floating layer, then the current layout.

        If we have have a currentWindow give it focus, optionally
        moving warp to it.
        """
        if self.screen and len(self.windows):
            with self.disableMask(xcb.xproto.EventMask.EnterWindow):
                normal = [x for x in self.windows if not x.floating]
                floating = [x for x in self.windows
                    if x.floating and not x.minimized]
                screen = self.screen.get_rect()
                if normal:
                    self.layout.layout(normal, screen)
                if floating:
                    self.floating_layout.layout(floating, screen)
                if self.currentWindow and self.screen == self.qtile.currentScreen:
                    self.currentWindow.focus(warp)

    def _setScreen(self, screen):
        """
        Set this group's screen to new_screen
        """
        if screen == self.screen:
            return
        self.screen = screen
        if self.screen:
            # move all floating guys offset to new screen
            self.floating_layout.to_screen(self.screen)
            self.layoutAll()
            rect = self.screen.get_rect()
            self.floating_layout.show(rect)
            self.layout.show(rect)
        else:
            self.hide()

    def hide(self):
        self.screen = None
        with self.disableMask(xcb.xproto.EventMask.EnterWindow
                              |xcb.xproto.EventMask.FocusChange
                              |xcb.xproto.EventMask.LeaveWindow):
            for i in self.windows:
                i.hide()
            self.layout.hide()

    @contextlib.contextmanager
    def disableMask(self, mask):
        for i in self.windows:
            i._disableMask(mask)
        yield
        for i in self.windows:
            i._resetMask()

    def focus(self, win, warp):
        """
            if win is in the group, blur any windows and call
            ``focus`` on the layout (in case it wants to track
            anything), fire focus_change hook and invoke layoutAll.

            warp - warp pointer to win
        """
        if self.qtile._drag:
            # don't change focus while dragging windows
            return
        if win and not win in self.windows:
            return
        if win:
            self.currentWindow = win
            if win.floating:
                for l in self.layouts:
                    l.blur()
                self.floating_layout.focus(win)
            else:
                self.floating_layout.blur()
                for l in self.layouts:
                    l.focus(win)
        else:
            self.currentWindow = None
        # !!! note that warp isn't hooked up now
        self.layoutAll(warp)

    def info(self):
        return dict(
            name = self.name,
            focus = self.currentWindow.name if self.currentWindow else None,
            windows = [i.name for i in self.windows],
            layout = self.layout.name,
            floating_info = self.floating_layout.info(),
            screen = self.screen.index if self.screen else None
        )

    def add(self, win):
        self.windows.add(win)
        win.group = self
        try:
            if self.floating_layout.match(win):
                # !!! tell it to float, can't set floating because it's too early
                # so just set the flag underneath
                win._float_state = window.floatStates.FLOATING
        except (xcb.xproto.BadWindow, xcb.xproto.BadAccess):
            pass  # doesn't matter
        if win.floating:
            self.floating_layout.add(win)
        else:
            for i in self.layouts:
                i.add(win)
        self.focus(win, True)

    def remove(self, win):

        self.windows.remove(win)
        win.group = None
        nextfocus = None
        if win.floating:
            nextfocus = self.floating_layout.remove(win)
            if nextfocus is None:
                nextfocus = self.layout.focus_first()
            if nextfocus is None:
                nextfocus = self.floating_layout.focus_first()
        else:
            for i in self.layouts:
                if i is self.layout:
                    nextfocus = i.remove(win)
                else:
                    i.remove(win)
            if nextfocus is None:
                nextfocus = self.floating_layout.focus_first()
            if nextfocus is None:
                nextfocus = self.layout.focus_first()
        self.focus(nextfocus, True)
        #else: TODO: change focus

    def mark_floating(self, win, floating):
        if floating and win in self.floating_layout.clients:
            # already floating
            pass
        elif floating:
            for i in self.layouts:
                i.remove(win)
                if win is self.currentWindow:
                    i.blur()
            self.floating_layout.add(win)
            if win is self.currentWindow:
                self.floating_layout.focus(win)
        else:
            self.floating_layout.remove(win)
            self.floating_layout.blur()
            for i in self.layouts:
                i.add(win)
                if win is self.currentWindow:
                    i.focus(win)
        self.layoutAll()

    def _items(self, name):
        if name == "layout":
            return True, range(len(self.layouts))
        elif name == "window":
            return True, [i.window.wid for i in self.windows]
        elif name == "screen":
            return True, None

    def _select(self, name, sel):
        if name == "layout":
            if sel is None:
                return self.layout
            else:
                return utils.lget(self.layouts, sel)
        elif name == "window":
            if sel is None:
                return self.currentWindow
            else:
                for i in self.windows:
                    if i.window.wid == sel:
                        return i
        elif name == "screen":
            return self.screen

    def cmd_setlayout(self, layout):
        self.layout = layout

    def cmd_info(self):
        """
            Returns a dictionary of info for this group.
        """
        return self.info()

    def cmd_toscreen(self, screen=None):
        """
            Pull a group to a specified screen.

            - screen: Screen offset. If not specified, we assume the current screen.

            Pull group to the current screen:
                toscreen()

            Pull group to screen 0:
                toscreen(0)
        """
        if not screen:
            screen = self.qtile.currentScreen
        else:
            screen = self.qtile.screens[screen]
        screen.setGroup(self)

    def _dirGroup(self, direction):
        currentgroup = self.qtile.groups.index(self)
        nextgroup = (currentgroup + direction) % len(self.qtile.groups)
        return self.qtile.groups[nextgroup]

    def prevGroup(self):
        return self._dirGroup(-1)

    def nextGroup(self):
        return self._dirGroup(1)

    # FIXME cmd_nextgroup and cmd_prevgroup should be on the Screen object.
    def cmd_nextgroup(self):
        """
            Switch to the next group.
        """
        n = self.nextGroup()
        self.qtile.currentScreen.setGroup(n)
        return n.name

    def cmd_prevgroup(self):
        """
            Switch to the previous group.
        """
        n = self.prevGroup()
        self.qtile.currentScreen.setGroup(n)
        return n.name

    def cmd_unminimise_all(self):
        """
            Unminimise all windows in this group.
        """
        for w in self.windows:
            w.minimised = False
        self.layoutAll()

    def cmd_next_window(self):
        if not self.windows:
            return
        if self.currentWindow.floating:
            nxt = self.floating_layout.focus_next(self.currentWindow)
            if not nxt:
                nxt = self.layout.focus_first()
            if not nxt:
                nxt = self.floating_layout.focus_first()
        else:
            nxt = self.layout.focus_next(self.currentWindow)
            if not nxt:
                nxt = self.floating_layout.focus_first()
            if not nxt:
                nxt = self.layout.focus_first()
        self.focus(nxt, True)

    def cmd_prev_window(self):
        if not self.windows:
            return
        if self.currentWindow.floating:
            nxt = self.floating_layout.focus_prev(self.currentWindow)
            if not nxt:
                nxt = self.layout.focus_last()
            if not nxt:
                nxt = self.floating_layout.focus_last()
        else:
            nxt = self.layout.focus_prev(self.currentWindow)
            if not nxt:
                nxt = self.floating_layout.focus_last()
            if not nxt:
                nxt = self.layout.focus_last()
        self.focus(nxt, True)


from orion.resources import default_config

class Nebula(SingletonPlugin):
    implements(IWindowManager)
    
    _exit = False
    def __init__(self):
        self.name = 'nebula'
        
        self.events = SignalGroup(
            'screen_create',
            'window_create',
            'key_press',
            'key_release',
            'window_create',
        )
        
    def init(self):
        config = default_config
        self.config = config
        hook.init(self)

        self.keyMap = {}
        self.windowMap = {}
        self.widgetMap = {}
        self.groupMap = {}
        self.groups = []
        
        # Find the modifier mask for the numlock key, if there is one:
        nc = orion.conn.keysym_to_keycode(orion.conn.keyboard.keysyms["Num_Lock"])
        self.numlockMask = orion.conn.keyboard.modmasks[orion.conn.get_modifier(nc)]
        self.validMask = ~(self.numlockMask | orion.conn.keyboard.modmasks["lock"])

        # Because we only do Xinerama multi-screening, we can assume that the first
        # screen's root is _the_ root.
        self.root = orion.conn.default_screen.root
        self.events.screen_create(self, screen=self.root)
        self.root.events.destroy_notify.connect(self.handle_DestroyNotify)
        self.root.events.configure_request.connect(self.handle_ConfigureRequest)
        hook.screen.configure_notify.connect(self.handle_ConfigureNotify)
        
        self.root.set_attribute(
            eventmask = EventMask.StructureNotify |\
                        EventMask.SubstructureNotify |\
                        EventMask.SubstructureRedirect |\
                        EventMask.EnterWindow |\
                        EventMask.LeaveWindow
        )

        if config.main:
            config.main(self)

        self.groups += self.config.groups[:]
        for i in self.groups:
            i._configure(config.layouts, config.floating_layout, self)
            self.groupMap[i.name] = i

        self.currentScreen = None
        self.screens = []
        self._process_screens()
        self.currentScreen = self.screens[0]
        self._drag = None

        '''
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
        ])'''
        self.ignoreEvents = set([
            xcb.xproto.ReparentNotifyEvent,
            xcb.xproto.CreateNotifyEvent,
            # DWM handles this to help "broken focusing windows".
            xcb.xproto.MapNotifyEvent,
            xcb.xproto.LeaveNotifyEvent,
            xcb.xproto.FocusOutEvent,
            xcb.xproto.FocusInEvent,
            xcb.xproto.NoExposureEvent
        ])
        
        
        if self._exit:
            print >> sys.stderr, "Access denied: Another window manager running?"
            sys.exit(1)

        #self.server = command._Server(self.fname, self, config)
        
        orion.conn.events.key_press += self.events.key_press
        orion.conn.events.key_release += self.events.key_release
        orion.conn.events.map_request += self.__handle_map_request
        
        self.mouseMap = {}
        for i in self.config.mouse:
            self.mouseMap[i.button_code] = i

        self.grabMouse()
        self.scan()
        
    def _process_screens(self):
        for screen in orion.conn.pseudoscreens:
            self.screens.append(screen)
        if not self.screens:
            s = Screen()
            self.currentScreen = s
            s._configure(
                self,
                0, 0, 0,
                orion.conn.default_screen.width_in_pixels,
                orion.conn.default_screen.height_in_pixels,
                self.groups[0],
            )
            self.screens.append(s)
        '''
        for i, s in enumerate(orion.conn.pseudoscreens):
            if i+1 > len(self.config.screens):
                scr = Screen()
            else:
                scr = self.config.screens[i]
            if not self.currentScreen:
                self.currentScreen = scr
            scr._configure(
                self,
                i,
                s.x,
                s.y,
                s.width,
                s.height,
                self.groups[i],
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
                orion.conn.default_screen.width_in_pixels,
                orion.conn.default_screen.height_in_pixels,
                self.groups[0],
            )
            self.screens.append(s)
        '''
            
    def mapKey(self, key):
        self.keyMap[(key.keysym, key.modmask&self.validMask)] = key
        code = orion.conn.keysym_to_keycode(key.keysym)
        self.root.grab_key(
            code,
            key.modmask,
            True,
            xcb.xproto.GrabMode.Async,
            xcb.xproto.GrabMode.Async,
        )
        if self.numlockMask:
            self.root.grab_key(
                code,
                key.modmask | self.numlockMask,
                True,
                xcb.xproto.GrabMode.Async,
                xcb.xproto.GrabMode.Async,
            )
            self.root.grab_key(
                code,
                key.modmask | self.numlockMask | window.proto.ModMasks["lock"],
                True,
                xcb.xproto.GrabMode.Async,
                xcb.xproto.GrabMode.Async,
            )

    def unmapKey(self, key):
        key_index = (key.keysym, key.modmask&self.validMask)
        if not key_index in self.keyMap:
            return

        code = orion.conn.keysym_to_keycode(key.keysym)
        self.root.ungrab_key(
            code,
            key.modmask)
        if self.numlockMask:
            self.root.ungrab_key(
                code,
                key.modmask | self.numlockMask
            )
            self.root.ungrab_key(
                code,
                key.modmask | self.numlockMask | window.proto.ModMasks["lock"]
            )
        del(self.keyMap[key_index])

    def addGroup(self, name):
        if name not in self.groupMap.keys():
            g = Group(name)
            self.groups.append(g)
            g._configure(self.config.layouts, self.config.floating_layout, self)
            self.groupMap[name] = g
            hook.fire("addgroup")
            return True
        return False

    def delGroup(self, name):
        if len(self.groups) == 1:
            raise ValueError("Can't delete all groups.")
        if name in self.groupMap.keys():
            group = self.groupMap[name]
            prev = group.prevGroup()
            for i in list(group.windows):
                i.togroup(prev.name)
            if self.currentGroup.name == name:
                self.currentGroup.cmd_prevgroup()
            self.groups.remove(group)
            del(self.groupMap[name])
            hook.fire("delgroup")

    @utils.LRUCache(200)
    def colorPixel(self, name):
        return orion.conn.screens[0].default_colormap.alloc_color(name).pixel

    @property
    def currentLayout(self):
        return self.currentGroup.layout

    @property
    def currentGroup(self):
        return self.currentScreen.group

    @property
    def currentWindow(self):
        return self.currentScreen.group.currentWindow

    def scan(self):
        _, _, children = self.root.query_tree()
        for item in children:
            try:
                attrs = item.get_attributes()
                state = item.get_wm_state()
            except (xcb.xproto.BadWindow, xcb.xproto.BadAccess):
                continue

            if attrs and attrs.map_state == xcb.xproto.MapState.Unmapped:
                continue
            if state and state[0] == window.wmState.WITHDRAWN:
                continue
            self.manage(item)
            

    def unmanage(self, win):
        c = self.windowMap.get(win)
        if c:
            hook.fire("client_killed", c)
            if getattr(c, "group", None):
                c.unmap()
                c.state = window.wmState.WITHDRAWN
                c.group.remove(c)
            del self.windowMap[win]

    def manage(self, w):
        try:
            attrs = w.get_attributes()
        except (xcb.xproto.BadWindow, xcb.xproto.BadAccess):
            return
        if attrs and attrs.override_redirect:
            return
        
        if not w.wid in self.windowMap:
            try:
                w.xxx()
                self.events.window_create(window=w)
                #c = window.Window(w, self)
            except (xcb.xproto.BadWindow, xcb.xproto.BadAccess):
                return
            # Window may be defunct because it's been declared static in hook.
            self.windowMap[w.wid] = w
            # Window may have been bound to a group in the hook.
            if not w.group:
                self.currentScreen.group.add(w)
            return w
        else:
            return self.windowMap[w.wid]

    def grabMouse(self):
        self.root.ungrab_button(None, None)
        for i in self.config.mouse:
            eventmask = EventMask.ButtonPress
            if isinstance(i, Drag):
                eventmask |= EventMask.ButtonRelease
            self.root.grab_button(
                i.button_code,
                i.modmask,
                True,
                eventmask,
                xcb.xproto.GrabMode.Async,
                xcb.xproto.GrabMode.Async,
                )
            if self.numlockMask:
                self.root.grab_button(
                    i.button_code,
                    i.modmask | self.numlockMask,
                    True,
                    eventmask,
                    xcb.xproto.GrabMode.Async,
                    xcb.xproto.GrabMode.Async,
                    )
                self.root.grab_button(
                    i.button_code,
                    i.modmask | self.numlockMask | window.proto.ModMasks["lock"],
                    True,
                    eventmask,
                    xcb.xproto.GrabMode.Async,
                    xcb.xproto.GrabMode.Async,
                    )

    def grabKeys(self):
        self.root.ungrab_key(None, None)
        for key in self.keyMap.values():
            self.mapKey(key)

    def get_target_chain(self, ename, e):
        """
            Returns a chain of targets that can handle this event. The event
            will be passed to each target in turn for handling, until one of
            the handlers returns False or the end of the chain is reached.
        """
        chain = []
        handler = "handle_%s"%ename
        # Certain events expose the affected window id as an "event" attribute.
        eventEvents = [
            "EnterNotify",
            "ButtonPress",
            "ButtonRelease",
            "KeyPress",
        ]
        c = None
        if hasattr(e, "window"):
            c = self.windowMap.get(e.window)
        elif hasattr(e, "drawable"):
            c = self.windowMap.get(e.drawable)
        elif ename in eventEvents:
            c = self.windowMap.get(e.event)

        if c and hasattr(c, handler):
            chain.append(getattr(c, handler))
        if hasattr(self, handler):
            chain.append(getattr(self, handler))
        if not chain:
            logger.debug("Unknown event: %r"%ename)
        return chain

    '''
    def _xpoll(self, conn=None, cond=None):
        eventEvents = [
            "EnterNotify",
            "ButtonPress",
            "ButtonRelease",
            "KeyPress",
        ]
        
        while True:
            e = orion.conn.conn.poll_for_event()
            if not e:
                break
            # This should be done in xpyb
            # client mesages start at 128
            if e.response_type >= 128:
                e = xcb.xproto.ClientMessageEvent(e)

            #ename = e.__class__.__name__
            e.name = e.__class__.__name__
            print '>>>>>>>', e.name
             
            if not e.__class__ in self.ignoreEvents:
                window = None
                if hasattr(e, "window"):
                    window = self.windowMap.get(e.window)
                elif hasattr(e, "drawable"):
                    window = self.windowMap.get(e.drawable)
                elif e.name in eventEvents:
                    window = self.windowMap.get(e.event)
                if not window:
                    print '!'
                    window = self.root
                
                window.handle_event(e)
        return True
    '''
    
    def run(self):

        #self.server.start()
        display_tag = gobject.io_add_watch(orion.conn.conn.get_file_descriptor(), gobject.IO_IN, orion.conn.xpoll)
        try:
            context = gobject.main_context_default()
            while True:
                if context.iteration(True):
                    try:
                        # this seems to be crucial part
                        orion.conn.flush()

                    # Catch some bad X exceptions. Since X is event based, race
                    # conditions can occur almost anywhere in the code. For
                    # example, if a window is created and then immediately
                    # destroyed (before the event handler is evoked), when the
                    # event handler tries to examine the window properties, it
                    # will throw a BadWindow exception. We can essentially
                    # ignore it, since the window is already dead and we've got
                    # another event in the queue notifying us to clean it up.
                    except (xcb.xproto.BadWindow, xcb.xproto.BadAccess):
                        # TODO: add some logging for this?
                        pass
                if self._exit:
                    break
        finally:
            gobject.source_remove(display_tag)

    def find_screen(self, x, y):
        """
            Find a screen based on the x and y offset.
        """
        result = []
        for i in self.screens:
            if x >= i.x and x <= i.x + i.width and y >= i.y and y <= i.y + i.height:
                result.append(i)
        if len(result) == 1:
            return result[0]
        return None

    def find_closest_screen(self, x, y):
        """
        If find_screen returns None, then this basically extends a
        screen vertically and horizontally and see if x,y lies in the
        band.

        Only works if it can find a SINGLE closest screen, else we
        revert to _find_closest_closest.

        Useful when dragging a window out of a screen onto another but
        having leftmost corner above viewport.
        """
        normal = self.find_screen(x, y)
        if normal is not None:
            return normal
        x_match = []
        y_match = []
        for i in self.screens:
            if x >= i.x and x <= i.x + i.width:
                x_match.append(i)
            if y >= i.y and y <= i.y + i.height:
                y_match.append(i)
        if len(x_match) == 1:
            return x_match[0]
        if len(y_match) == 1:
            return y_match[0]
        return self._find_closest_closest(x, y, x_match + y_match)

    def _find_closest_closest(self, x, y, candidate_screens):
        """
        if find_closest_screen can't determine one, we've got multiple
        screens, so figure out who is closer.  We'll calculate using
        the square of the distance from the center of a screen.

        Note that this could return None if x, y is right/below all
        screens (shouldn't happen but we don't do anything about it
        here other than returning None)
        """
        closest_distance = None
        closest_screen = None
        if not candidate_screens:
            # try all screens
            candidate_screens = self.screens
        # if left corner is below and right of screen it can't really be a candidate
        candidate_screens = [s for s in candidate_screens if x < s.x + s.width and y < s.y + s.width]
        for s in candidate_screens:
            middle_x = s.x + s.width/2
            middle_y = s.y + s.height/2
            distance = (x - middle_x)**2 + (y - middle_y)**2
            if closest_distance is None or distance < closest_distance:
                closest_distance = distance
                closest_screen = s
        return closest_screen

    def handle_EnterNotify(self, e):
        if e.event in self.windowMap:
            return True
        s = self.find_screen(e.root_x, e.root_y)
        if s:
            self.toScreen(s.index)

    def handle_KeyPress(self, e):
        import subprocess
        subprocess.Popen('gnome-terminal')
        return
        '''
        keysym = orion.conn.code_to_syms[e.detail][0]
        state = e.state
        if self.numlockMask:
            state = e.state | self.numlockMask
        k = self.keyMap.get((keysym, state&self.validMask))
        if not k:
            print >> sys.stderr, "Ignoring unknown keysym: %s"%keysym
            return
        for i in k.commands:
            if i.check(self):
                status, val = self.server.call((i.selectors, i.name, i.args, i.kwargs))
                if status in (command.ERROR, command.EXCEPTION):
                    s = "KB command error %s: %s"%(i.name, val)
                    self.log.add(s)
                    print >> sys.stderr, s
        else:
            return
        '''

    def handle_ButtonPress(self, e):
        button_code = e.detail
        state = e.state
        if self.numlockMask:
            state = e.state | self.numlockMask

        m = self.mouseMap.get(button_code)
        if not m or m.modmask&self.validMask != state&self.validMask:
            print >> sys.stderr, "Ignoring unknown button: %s"%button_code
            return
        if isinstance(m, Click):
            for i in m.commands:
                if i.check(self):
                    status, val = self.server.call((i.selectors, i.name, i.args, i.kwargs))
                    if status in (command.ERROR, command.EXCEPTION):
                        s = "Mouse command error %s: %s"%(i.name, val)
                        self.log.add(s)
                        print >> sys.stderr, s
        elif isinstance(m, Drag):
            x = e.event_x
            y = e.event_y
            if m.start:
                i = m.start
                status, val = self.server.call((i.selectors, i.name, i.args, i.kwargs))
                if status in (command.ERROR, command.EXCEPTION):
                    s = "Mouse command error %s: %s"%(i.name, val)
                    self.log.add(s)
                    print >> sys.stderr, s
                    return
            else:
                val = 0, 0
            self._drag = x, y, val[0], val[1], m.commands
            self.root.grab_pointer(
                True,
                window.proto.ButtonMotionMask | window.proto.AllButtonsMask | window.proto.ButtonReleaseMask,
                xcb.xproto.GrabMode.Async,
                xcb.xproto.GrabMode.Async,
                )

    def handle_ButtonRelease(self, e):
        button_code = e.detail
        state = e.state & ~window.proto.AllButtonsMask
        if self.numlockMask:
            state = state | self.numlockMask
        m = self.mouseMap.get(button_code)
        if not m:
            print >> sys.stderr, "Ignoring unknown button release: %s"%button_code
            return
        if isinstance(m, Drag):
            self._drag = None
            self.root.ungrab_pointer()

    def handle_MotionNotify(self, e):
        if self._drag is None:
            return
        ox, oy, rx, ry, cmd = self._drag
        dx = e.event_x - ox
        dy = e.event_y - oy
        if dx or dy:
            for i in cmd:
                if i.check(self):
                    status, val = self.server.call((i.selectors, i.name, i.args + (rx+dx, ry+dy), i.kwargs))
                    if status in (command.ERROR, command.EXCEPTION):
                        s = "Mouse command error %s: %s"%(i.name, val)
                        self.log.add(s)
                        print >> sys.stderr, s

    def handle_ConfigureNotify(self, e):
        """
            Handle xrandr events.
        """
        screen = self.currentScreen
        if e.window == self.root.wid and e.width != screen.width and e.height != screen.height:
            screen.resize(0, 0, e.width, e.height)

    def handle_ConfigureRequest(self, e):
        '''
        tylko dla okienka root!
        '''
        # It's not managed, or not mapped, so we just obey it.
        cw = xcb.xproto.ConfigWindow
        args = {}
        if e.value_mask & cw.X:
            args["x"] = max(e.x, 0)
        if e.value_mask & cw.Y:
            args["y"] = max(e.y, 0)
        if e.value_mask & cw.Height:
            args["height"] = max(e.height, 0)
        if e.value_mask & cw.Width:
            args["width"] = max(e.width, 0)
        if e.value_mask & cw.BorderWidth:
            args["borderwidth"] = max(e.border_width, 0)
        w = Window(orion.conn, e.window, self)
        w.configure(**args)

    def handle_MappingNotify(self, e):
        orion.conn.refresh_keymap()
        if e.request == xcb.xproto.Mapping.Keyboard:
            self.grabKeys()

    def __handle_map_request(self, e):
        w = Window(orion.conn, e.wid)
        c = self.manage(w)
        if c and (not c.group or not c.group.screen):
            return
        w.map()

    def handle_DestroyNotify(self, e):
        self.unmanage(e.window)

    def handle_UnmapNotify(self, e):
        RESPONSE_TYPE_MASK = 0x7f
        SEND_EVENT_MASK = 0x80
        if e.event != self.root.wid:
            self.unmanage(e.window)

    def toScreen(self, n):
        """
        Have Qtile move to screen and put focus there
        """
        if len(self.screens) < n-1:
            return
        self.currentScreen = self.screens[n]
        self.currentGroup.focus(
            self.currentWindow,
            True
        )

    def moveToGroup(self, group):
        """
            Create a group if it dosn't exist and move a windows there
        """
        if self.currentWindow and group:
            self.addGroup(group)
            self.currentWindow.togroup(group)

    def _items(self, name):
        if name == "group":
            return True, self.groupMap.keys()
        elif name == "layout":
            return True, range(len(self.currentGroup.layouts))
        elif name == "widget":
            return False, self.widgetMap.keys()
        elif name == "bar":
            return False, [x.position for x in self.currentScreen.gaps]
        elif name == "window":
            return True, self.listWID()
        elif name == "screen":
            return True, range(len(self.screens))

    def _select(self, name, sel):
        if name == "group":
            if sel is None:
                return self.currentGroup
            else:
                return self.groupMap.get(sel)
        elif name == "layout":
            if sel is None:
                return self.currentGroup.layout
            else:
                return utils.lget(self.currentGroup.layouts, sel)
        elif name == "widget":
            return self.widgetMap.get(sel)
        elif name == "bar":
            return getattr(self.currentScreen, sel)
        elif name == "window":
            if sel is None:
                return self.currentWindow
            else:
                return self.clientFromWID(sel)
        elif name == "screen":
            if sel is None:
                return self.currentScreen
            else:
                return utils.lget(self.screens, sel)

    def listWID(self):
        return [i.window.wid for i in self.windowMap.values()]

    def clientFromWID(self, wid):
        for i in self.windowMap.values():
            if i.window.wid == wid:
                return i
        return None

    def cmd_groups(self):
        """
            Return a dictionary containing information for all groups.

            Example:

                groups()
        """
        d = {}
        for i in self.groups:
            d[i.name] = i.info()
        return d

    def cmd_list_widgets(self):
        """
            List of all addressible widget names.
        """
        return self.widgetMap.keys()

    def cmd_log(self, n=None):
        """
            Return the last n log records, where n is all by default.

            Examples:

                log(5)

                log()
        """
        if n and len(self.log.log) > n:
            return self.log.log[-n:]
        else:
            return self.log.log

    def cmd_log_clear(self):
        """
            Clears the internal log.
        """
        self.log.clear()

    def cmd_log_getlength(self):
        """
            Returns the configured size of the internal log.
        """
        return self.log.length

    def cmd_log_setlength(self, n):
        """
            Sets the configured size of the internal log.
        """
        return self.log.setLength(n)

    def cmd_nextlayout(self, group=None):
        """
            Switch to the next layout.

            :group Group name. If not specified, the current group is assumed.
        """
        if group:
            group = self.groupMap.get(group)
        else:
            group = self.currentGroup
        group.nextLayout()

    def cmd_prevlayout(self, group=None):
        """
            Switch to the prev layout.

            :group Group name. If not specified, the current group is assumed.
        """
        if group:
            group = self.groupMap.get(group)
        else:
            group = self.currentGroup
        group.prevLayout()

    def cmd_report(self, msg="None", path="~/qtile_crashreport"):
        """
            Write a qtile crash report.

            :msg Message that should head the report
            :path Path of the file to write to

            Examples:

                report()

                report(msg="My messasge")

                report(msg="My message", path="~/myreport")
        """
        self.writeReport(msg, path, True)

    def cmd_screens(self):
        """
            Return a list of dictionaries providing information on all screens.
        """
        lst = []
        for i in self.screens:
            lst.append(dict(
                index = i.index,
                group = i.group.name if i.group is not None else None,
                x = i.x,
                y = i.y,
                width = i.width,
                height = i.height,
                gaps = dict(
                    top = i.top.geometry() if i.top else None,
                    bottom = i.bottom.geometry() if i.bottom else None,
                    left = i.left.geometry() if i.left else None,
                    right = i.right.geometry() if i.right else None,
                )
            ))
        return lst

    def cmd_simulate_keypress(self, modifiers, key):
        """
            Simulates a keypress on the focused window.

            :modifiers A list of modifier specification strings. Modifiers can
            be one of "shift", "lock", "control" and "mod1" - "mod5".
            :key Key specification.

            Examples:

                simulate_keypress(["control", "mod2"], "k")
        """
        # FIXME: This needs to be done with sendevent, once we have that fixed.
        keysym = keyboard.keysyms.get(key)
        if keysym is None:
            raise command.CommandError("Unknown key: %s"%key)
        keycode = orion.conn.first_sym_to_code[keysym]
        class DummyEv:
            pass

        d = DummyEv()
        d.detail = keycode
        try:
            d.state = utils.translateMasks(modifiers)
        except KeyError, v:
            return v.args[0]
        self.handle_KeyPress(d)

    def cmd_execute(self, cmd, args):
        """
            Executes the specified command, replacing the current process.
        """
        atexit._run_exitfuncs()
        os.execv(cmd, args)

    def cmd_restart(self):
        """
            Restart qtile using the execute command.
        """
        self.cmd_execute(sys.executable, [sys.executable] + sys.argv)

    def cmd_spawn(self, cmd):
        """
            Run cmd in a shell.

            Example:

                spawn("firefox")
        """
        gobject.spawn_async([os.environ['SHELL'], '-c', cmd])

    def cmd_status(self):
        """
            Return "OK" if Qtile is running.
        """
        return "OK"

    def cmd_sync(self):
        """
            Sync the X display. Should only be used for development.
        """
        orion.conn.flush()

    def cmd_to_screen(self, n):
        """
            Warp focus to screen n, where n is a 0-based screen number.

            Example:

                to_screen(0)
        """
        return self.toScreen(n)

    def cmd_to_next_screen(self):
        """
            Move to next screen
        """
        return self.toScreen((self.screens.index(self.currentScreen) + 1 ) % len(self.screens))

    def cmd_to_prev_screen(self):
        """
            Move to the previous screen
        """
        return self.toScreen((self.screens.index(self.currentScreen) - 1) % len(self.screens))

    def cmd_windows(self):
        """
            Return info for each client window.
        """
        return [i.info() for i in self.windowMap.values() if not isinstance(i, window.Internal)]

    def cmd_internal_windows(self):
        """
            Return info for each internal window (bars, for example).
        """
        return [i.info() for i in self.windowMap.values() if isinstance(i, window.Internal)]

    def cmd_info(self):
        """
            Returns a dictionary of info on the Qtile instance.
        """
        return dict(
            socketname = self.fname
        )

    def cmd_shutdown(self):
        """
            Quit Qtile.
        """
        self._exit = True

    def cmd_togroup(self, prompt="group: ", widget="prompt"):
        """
            Move current window to the selected group in a propmt widget

            prompt: Text with which to prompt user.
            widget: Name of the prompt widget (default: "prompt").
        """
        if not self.currentWindow:
            self.log.add("No window to move")
            return

        mb = self.widgetMap.get(widget)
        if not mb:
            self.log.add("No widget named '%s' present." % widget)
            return

        mb.startInput(prompt, self.moveToGroup, "group")

    def cmd_switchgroup(self, prompt="group: ", widget="prompt"):
        def f(group):
            if group:
                try:
                    self.groupMap[group].cmd_toscreen()
                except KeyError:
                    self.log.add("No group named '%s' present." % group)
                    pass

        mb = self.widgetMap.get(widget)
        if not mb:
            self.log.add("No widget named '%s' present." % widget)
            return

        mb.startInput(prompt, f, "group")

    def cmd_spawncmd(self, prompt="spawn: ", widget="prompt"):
        """
            Spawn a command using a prompt widget, with tab-completion.

            prompt: Text with which to prompt user.
            widget: Name of the prompt widget (default: "prompt").
        """
        try:
            mb = self.widgetMap[widget]
            mb.startInput(prompt, self.cmd_spawn, "cmd")
        except:
            self.log.add("No widget named '%s' present."%widget)

    def cmd_addgroup(self, group):
        return self.addGroup(group)

    def cmd_delgroup(self, group):
        return self.delGroup(group)

    def cmd_eval(self, code):
        """
            Evaluates code in the same context as this function.
            Return value is (success, result), success being a boolean and
            result being a string representing the return value of eval, or
            None if exec was used instead.
        """
        try:
            try:
                return (True, str(eval(code)))
            except SyntaxError:
                exec code
                return (True, None)
        except:
            error = traceback.format_exc().strip().split("\n")[-1]
            return (False, error)

    def cmd_function(self, function):
        """ Call a function with qtile instance as argument """
        try:
            function(self)
        except Exception:
            error = traceback.format_exc().strip().split("\n")[-1]
            self.log.add('Can\'t call "%s": %s' % (function, error))
