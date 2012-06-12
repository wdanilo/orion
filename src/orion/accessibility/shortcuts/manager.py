import inspect
from pyutilib.component.core import implements, SingletonPlugin
from orion.accessibility.api import IShortcutManager
from command import Command
import orion

import logging
logger = logging.getLogger(__name__)

class ShortcutManager(SingletonPlugin):
    implements(IShortcutManager)
    
    def __init__(self):
        self.cmd = Command()
        
    def register(self, *args):
        keys = args[:-1]
        key = keys[-1]
        mods = keys[:-1]
        command = args[-1]
        if not keys or not command:
            logger.error("Cannot register shortcut!")
        orion.window_manager.root.grab_key(key, mods)
        
    
