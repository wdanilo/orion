from pyutilib.component.core import ExtensionPoint
from api import IShortcutManager, IGestureManager

class Accessibility(object):
    def __init__(self):
        self.__shortcut_manager = None
        self.__gesture_manager = None
        
        self.__shortcut_managers = ExtensionPoint(IShortcutManager)
        self.__gesture_managers = ExtensionPoint(IGestureManager)
        
        print '!!!'