from orion.model.logger import Logger
from orion.wm.api import IWindowManager
from pyutilib.component.core import ExtensionPoint, PluginGlobals
from orion.accessibility import AccessibilityManager

import logging
logger = logging.getLogger(__name__)

class Orion(object):
    def __init__(self):
        self.__window_managers = ExtensionPoint(IWindowManager)
        self.__accessibility_manager = None
        
    
    def run(self):
        self.__accessibility_manager = AccessibilityManager()
        
        self.DEBUG_TEST()
        
        PluginGlobals.push_env('orion')
        l = Logger('orion', verbose=True)
        manager_count = len(self.__window_managers)
        logger.debug('found %s orion window managers'%manager_count)
        manager = self.__window_managers()[0]
        logger.debug("starting '%s' window manager"%manager.name)
        manager.run()
        PluginGlobals.pop_env('orion')
        
    def f(self):
        print '!!!!'
        
    def DEBUG_TEST(self):
        import subprocess
        sm = self.__accessibility_manager.shortcut_manager
        cmd = sm.cmd
        sm.register('mod4', 'z', cmd.subprocess.Popen('gnome-terminal'))

import orion, sys
orion_inst = Orion()
orion_inst.__file__ = orion.__file__
orion_inst.__path__  = orion.__path__
sys.modules['orion'] = orion_inst

################# DEBUG
from orion.wm import nebula
from orion.accessibility.shortcuts import manager
#######################