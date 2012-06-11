import inspect
from pyutilib.component.core import implements, SingletonPlugin
from orion.accessibility.api import IShortcutManager
from command import Command

import logging
logger = logging.getLogger(__name__)

class ShortcutManager(SingletonPlugin):
    implements(IShortcutManager)
    
    def __init__(self):
        self.cmd = Command()
        
    def register(self, *args):
        keys = args[:-1]
        command = args[-1] if args else None
        if not keys or not command:
            logger.error("Cannot register shortcut!")
        
    
