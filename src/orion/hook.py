import manager
from orion.utils import pack

subscriptions = {}
SKIPLOG = set()

import logging
logger = logging.getLogger(__name__)

from orion.signals import Signal

window = pack(
    on_create               = Signal(),
    on_mouse_enter          = Signal(),
    on_key_press            = Signal(),
    on_key_release          = Signal(),
    on_map_request          = Signal(),
    on_destroy_notify       = Signal(),
    on_property_notify      = Signal(),
    on_client_message       = Signal(),
    on_configure_request    = Signal(),
    on_configure_notify     = Signal(),
)

screen = pack(
    on_create               = Signal(),
    on_mouse_enter          = Signal(),
    on_key_press            = Signal(),
    on_key_release          = Signal(),
    on_map_request          = Signal(),
    on_destroy_notify       = Signal(),
    on_property_notify      = Signal(),
    on_client_message       = Signal(),
    on_configure_request    = Signal(),
    on_configure_notify     = Signal(),
)

def test_terminal(e):
    import subprocess
    subprocess.Popen('gnome-terminal')

def f(e):
    print '!!!'
    print e.target
    print e.currentTarget
    
window.on_mouse_enter.connect(f)
screen.on_key_press.connect(test_terminal)

def manage_window(e):
    w = e.window
    w.on_mouse_enter.       connect(window.on_mouse_enter)
    w.on_key_press.         connect(window.on_key_press)
    w.on_key_release.       connect(window.on_key_release)
    w.on_map_request.       connect(window.on_map_request)
    w.on_destroy_notify.    connect(window.on_destroy_notify)
    w.on_property_notify.   connect(window.on_property_notify)
    w.on_client_message.    connect(window.on_client_message)
    w.on_configure_request. connect(window.on_configure_request)
    w.on_configure_notify.  connect(window.on_configure_notify)
    
def manage_screen(e):
    w = e.screen
    w.on_mouse_enter.       connect(screen.on_mouse_enter)
    w.on_key_press.         connect(screen.on_key_press)
    w.on_key_release.       connect(screen.on_key_release)
    w.on_map_request.       connect(screen.on_map_request)
    w.on_destroy_notify.    connect(screen.on_destroy_notify)
    w.on_property_notify.   connect(screen.on_property_notify)
    w.on_client_message.    connect(screen.on_client_message)
    w.on_configure_request. connect(screen.on_configure_request)
    w.on_configure_notify.  connect(screen.on_configure_notify)

def init(orion):
    orion.on_window_create.connect(window.on_create)
    orion.on_window_create.connect(manage_window)
    orion.on_screen_create.connect(screen.on_create)
    orion.on_screen_create.connect(manage_screen)


def clear():
    subscriptions.clear()


class Subscribe:
    def __init__(self):
        hooks = set([])
        for i in dir(self):
            if not i.startswith("_"):
                hooks.add(i)
        self.hooks = hooks
        
    def _subscribe(self, event, func):
        lst = subscriptions.setdefault(event, [])
        if not func in lst:
            lst.append(func)

    def startup(self, func):
        """
            Called when Qtile has initialized
        """
        return self._subscribe("startup", func)

    def setgroup(self, func):
        """
            Called when group is changed.
        """
        return self._subscribe("setgroup", func)

    def addgroup(self, func):
        """
            Called when group is added.
        """
        return self._subscribe("addgroup", func)

    def delgroup(self, func):
        """
            Called when group is deleted.
        """
        return self._subscribe("delgroup", func)

    def focus_change(self, func):
        """
            Called when focus is changed.
        """
        return self._subscribe("focus_change", func)

    def float_change(self, func):
        """
            Called when a change in float state is made
        """
        return self._subscribe("float_change", func)

    def group_window_add(self, func):
        """
            Called when a new window is added to a group.
        """
        return self._subscribe("group_window_add", func)

    def window_name_change(self, func):
        """
            Called whenever a windows name changes.
        """
        return self._subscribe("window_name_change", func)

    def client_new(self, func):
        """
            Called before Qtile starts managing a new client. Use this hook to
            declare windows static, or add them to a group on startup. This
            hook is not called for internal windows.

            - arguments: window.Window object

            ## Example:

                def func(c):
                    if c.name == "xterm":
                        c.togroup("a")
                    elif c.name == "dzen":
                        c.static(0)
                libqtile.hook.subscribe.client_new(func)
        """
        return self._subscribe("client_new", func)

    def client_managed(self, func):
        """
            Called after Qtile starts managing a new client. That is, after a
            window is assigned to a group, or when a window is made static.
            This hook is not called for internal windows.
            
            - arguments: window.Window object
        """
        return self._subscribe("client_managed", func)

    def client_killed(self, func):
        """
            Called after a client has been unmanaged.

            - arguments: window.Window object of the killed window.
        """
        return self._subscribe("client_killed", func)

    def client_state_changed(self, func):
        """
            Called whenever client state changes.
        """
        return self._subscribe("client_state_changed", func)

    def client_type_changed(self, func):
        """
            Called whenever window type changes.
        """
        return self._subscribe("client_type_changed", func)

    def client_focus(self, func):
        """
            Called whenver focus changes.

            - arguments: window.Window object of the new focus.
        """
        return self._subscribe("client_focus", func)

    def client_mouse_enter(self, func):
        """
            Called when the mouse enters a client.
        """
        return self._subscribe("client_mouse_enter", func)

    def client_name_updated(self, func):
        """
            Called when the client name changes.
        """
        return self._subscribe("client_name_updated", func)

    def client_urgent_hint_changed(self, func):
        """
            Called when the client urgent hint changes.
        """
        return self._subscribe("client_urgent_hint_changed", func)

    def layout_change(self, func):
        """
            Called on layout change.
        """
        return self._subscribe("layout_change", func)

subscribe = Subscribe()

class Unsubscribe(Subscribe):
    """
        This class mirrors subscribe, except the _subscribe member has been
        overridden to removed calls from hooks.
    """
    def _subscribe(self, event, func):
        lst = subscriptions.setdefault(event, [])
        try:
            lst.remove(func)
        except ValueError:
            raise manager.QtileError("Tried to unsubscribe a hook that was not currently subscribed")


unsubscribe = Unsubscribe()

def fire(event, *args, **kwargs):
    if event not in subscribe.hooks:
        raise manager.QtileError("Unknown event: %s"%event)
    if not event in SKIPLOG:
        logger.debug("Internal event: %s(%s, %s)"%(event, args, kwargs))
    for i in subscriptions.get(event, []):
        i(*args, **kwargs)
