version = '0.1a'

from pyutilib.component.core import ExtensionPoint, PluginGlobals
from orion.api import IOrionPlugin
from orion.model.cmdparser import CmdParser
from orion.model.logger import Logger

import os
import sys
import logging
logger = logging.getLogger(__name__)

class Orion ( object ) :
    wmcore = ExtensionPoint(IOrionPlugin)
    
    def __init__ (self):
        self.tasks     = {}
        self.cmdparser = CmdParser()
        self.logger    = Logger('orion', self.cmdparser.args)

    def run(self):
        # fixing logging message types
        PluginGlobals.env().log.info = PluginGlobals.env().log.debug
        #PluginGlobals.env().log.warning = PluginGlobals.env().log.debug
        PluginGlobals.push_env('orion')
        PluginGlobals.env().log.info = PluginGlobals.env().log.debug
        
        # prepare eggLoader instance
        from pyutilib.component.loader import EggLoader
        _ = EggLoader(namespace='orion')
        
        # read plugin paths and load plugins
        paths = os.environ['ORION_PLUGIN_PATH'].split(os.pathsep)
        PluginGlobals.load_services( path=paths,  auto_disable=False)
        
        # parse cmd araguments
        self.cmdparser.parse()
        
        logger.info('Orion Core started')
        
        ''' DEBUG '''
        import core
        '''  '''
        
        # test plugins
        wmcores = self.wmcore.extensions()
        if len(wmcores)>1:
            logger.warning("more than 1 wmcore found. Selecting the first one.")
        elif len(wmcores) == 0:
            logger.critical('no wmcore plugins found. exiting.')
            sys.exit()
        wmcores[0].init()
        
        # clean env
        PluginGlobals.pop_env()

def run():
    orion = Orion()
    orion.run()
    
