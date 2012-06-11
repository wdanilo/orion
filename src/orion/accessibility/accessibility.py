from pyutilib.component.core import ExtensionPoint
from api import IShortcutManager, IGestureManager

class AccessibilityManager(object):
    def __init__(self):
        self.__shortcut_manager = None
        self.__gesture_manager = None
        
        self.__shortcut_managers = ExtensionPoint(IShortcutManager)
        self.__gesture_managers = ExtensionPoint(IGestureManager)
        
        self.__shortcut_manager = self.__shortcut_managers()[0]
        
    @property
    def shortcut_manager(self):
        return self.__shortcut_manager