import inspect
from pyutilib.component.core import implements, SingletonPlugin
from orion.accessibility.api import IShortcutManager

class ShortcutManager(SingletonPlugin):
    implements(IShortcutManager)
    def register(self, modifiers, key, *commands):
        pass
    




#cmd = Command()
