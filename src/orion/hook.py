from orion.utils import pack

import logging
logger = logging.getLogger(__name__)

from orion.signals import Signal, SignalGroup

window = SignalGroup(
    'create',        
    'mouse_enter',        
    'key_press',        
    'key_release',        
    'map_request',        
    'destroy_notify',        
    'property_notify',        
    'client_message',        
    'configure_request',        
    'configure_notify',        
)

screen = SignalGroup(
    'create',
    'mouse_enter',
    'key_press',
    'key_release',
    'map_request',
    'destroy_notify',
    'property_notify',
    'client_message',
    'configure_request',
    'configure_notify',
)

def test_terminal(e):
    import subprocess
    subprocess.Popen('gnome-terminal')

def f(e):
    print '!!!'
    print e.target
    print e.currentTarget
    
window.mouse_enter.connect(f)
screen.key_press.connect(test_terminal)

def manage_window(e):
    e.window.events.connect_by_name(window)
    
def manage_screen(e):
    e.screen.events.connect_by_name(screen)

def init(orion):
    orion.events.window_create.connect(window.create)
    orion.events.window_create.connect(manage_window)
    orion.events.screen_create.connect(screen.create)
    orion.events.screen_create.connect(manage_screen)
