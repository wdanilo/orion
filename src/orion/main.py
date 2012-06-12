from orion.model.logger import Logger
from orion.wm.api import IWindowManager
from pyutilib.component.core import ExtensionPoint, PluginGlobals
from orion.accessibility import AccessibilityManager
from orion.comm.api import IDisplayServerCommunicator
import os

import logging
logger = logging.getLogger(__name__)

class Orion(object):
    def __init__(self):
        self.__window_managers = ExtensionPoint(IWindowManager)
        self.__display_servers = ExtensionPoint(IDisplayServerCommunicator)
        self.__accessibility_manager = None
        self.__conn = None
        
    
    def run(self):
        self.__accessibility_manager = AccessibilityManager()
        
        PluginGlobals.push_env('orion')
        l = Logger('orion', verbose=True)
        manager_count = len(self.__window_managers)
        logger.debug('found %s orion window managers'%manager_count)
        manager = self.__window_managers()[0]
        
        displayName = os.environ.get("DISPLAY")
        if not displayName:
            raise 
        self.__conn = self.__display_servers()[0]
        self.__conn.init(displayName, manager)
        self.__conn.events.key_press += manager.events.key_press
        self.__conn.events.key_release += manager.events.key_release
        self.__conn.events.map_request += manager._Nebula__handle_map_request
        
        manager.init()
        
        
        self.DEBUG_TEST()
        
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
    
    @property
    def conn(self): return self.__conn

import orion, sys
orion_inst = Orion()
orion_inst.__file__ = orion.__file__
orion_inst.__path__  = orion.__path__
sys.modules['orion'] = orion_inst

################# DEBUG
from orion.wm import nebula
from orion.accessibility.shortcuts import manager
from orion.comm.xorg import xorg
#######################