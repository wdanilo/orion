from pyutilib.component.core import *
from orion.api import IOrionPlugin

import os
import sys
from orion.core import comm

from orion.core.comm.connection import Connection
#from orion.core.comm import xcbq
from orion.core.comm.connection import keyboard
import xcb
from orion.core.comm import Server
import gobject
from orion.core import window
#from orion.core.comm.connection import keyboard

import logging
logger = logging.getLogger(__name__)

class CoreError(Exception): pass

def f (event):
    from random import random
    print 'TO DELETE '*10
    event.target.x+=int((random()-0.5)*100)
    
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
        self.conn = Connection(displayName)

        # Find the modifier mask for the numlock key, if there is one:
        nc = self.conn.keysym_to_keycode(keyboard.keysyms["Num_Lock"])
        self.numlockMask = keyboard.ModMasks[self.conn.get_modifier(nc)]
        self.validMask = ~(self.numlockMask | keyboard.ModMasks["lock"])
        
        self.root = self.conn.defaultScreen.root
        self.windowMap = {}
        
        
        self.ignoreEvents = (
            xcb.xproto.KeyReleaseEvent,
            xcb.xproto.ReparentNotifyEvent,
            xcb.xproto.CreateNotifyEvent,
            # DWM handles this to help "broken focusing windows".
            xcb.xproto.MapNotifyEvent,
            xcb.xproto.LeaveNotifyEvent,
            xcb.xproto.FocusOutEvent,
            xcb.xproto.FocusInEvent,
            xcb.xproto.NoExposureEvent
        )
        
        self.conn.flush()
        self.conn.xsync()
        self._xpoll()
        
        #self.server = Server(self.sockname, self)
        self.scan()
        
        ## run loop!
        self.loop()
    
    def loop(self):
        #self.server.start()
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
        # Certain events expose the affected window id as an "event" attribute.
        eventEvents = [
            "EnterNotify",
            "ButtonPress",
            "ButtonRelease",
            "KeyPress",
        ]
        
        while True:
            #try:
            e = self.conn.conn.poll_for_event()
            if not e:
                break
#            print e
#            print dir(e)
#            print e.response_type
#            print __file__
            # This should be done in xpyb
            # client mesages start at 128
            if e.response_type >= 128:
                e = xcb.xproto.ClientMessageEvent(e)

            ename = e.__class__.__name__

            if ename.endswith("Event"):
                ename = ename[:-5]
            if not e.__class__ in self.ignoreEvents:
                window = None
                if hasattr(e, "window"):
                    window = self.windowMap.get(e.window)
                elif ename in eventEvents:
                    window = self.windowMap.get(e.event)
                if window: window.handleEvent(ename, e)
                self.handleEvent(ename, e)
                
            '''except Exception, v:
                raise v
                self.errorHandler(v)
                if self._exit:
                    return False
                continue
            '''
        return True
    
    def handleEvent(self, name, e):
        print '!', name, hasattr(e, "window")
        if name == 'EnterNotify':
            print dir(e)
            print e.detail
            window = self.windowMap.get(e.child)
            if window: window.handleEvent(name, e)
            print window
    
    def scan(self):
        for item in self.root.children():
            try:
                attrs = item.attributes()
                state = item.state
            except (xcb.xproto.BadWindow, xcb.xproto.BadAccess):
                continue
# tego ponizej nie, bo np w eclipsie latajace okienka sien ie zalapuja!
#            if attrs and attrs.map_state == xcb.xproto.MapState.Unmapped:
#                continue
            if state and state == window.iccm.WithdrawnState:
                continue
#            print item.name
            self.manage(item)
    
    def manage(self, w):
        w.onMouseEnter.connect(f)
        try:
            attrs = w.attributes()
        except (xcb.xproto.BadWindow, xcb.xproto.BadAccess):
            return
        if attrs and attrs.override_redirect:
            return

        if not w.wid in self.windowMap:
            self.windowMap[w.wid] = w
            return w
        else:
            return self.windowMap[w.wid]
        



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

