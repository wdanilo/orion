from orion.model.logger import Logger
from orion.wm.api import IWindowManager
from pyutilib.component.core import ExtensionPoint, PluginGlobals

import logging
logger = logging.getLogger(__name__)

################# DEBUG
from orion.wm import nebula


#######################

class Orion(object):
    def __init__(self):
        self.__window_managers = ExtensionPoint(IWindowManager)
        print self.__window_managers()
    
    def run(self):
        PluginGlobals.push_env('orion')
        l = Logger('orion', verbose=True)
        manager_count = len(self.__window_managers)
        logger.debug('found %s orion window managers'%manager_count)
        manager = self.__window_managers()[0]
        logger.debug("starting '%s' window manager"%manager.name)
        manager.run()
        PluginGlobals.pop_env('orion')

def run():
    orion = Orion()
    orion.run()