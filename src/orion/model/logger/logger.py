import tempfile
import sys
import os
import atexit

from colorFormatter import ExtendedFormatter
import logging
logger = logging.getLogger(__name__)

class Logger():
    def __init__(self, name, args):
        if args.verbose:
            verboseLevel = logging.DEBUG 
            formatmsg = '%(levelname)s\t%(message)s (%(name)s)'
        else:
            if args.silent:
                verboseLevel = logging.ERROR
            else:
                verboseLevel = logging.INFO
                
            formatmsg = '%(message)s'
            
        formatter = ExtendedFormatter('%(levelname)s %(message)s','%Y:%m:%d:%H:%M:%S', not args.no_color, args.use_ident)
        
        self.rootLogger = logging.root
        self.rootLogger.setLevel(logging.DEBUG)
        self.__name          = name
        self.__streamHandler = logging.StreamHandler()
        self.__streamHandler.setFormatter(formatter)
        self.__streamHandler.setLevel(verboseLevel)
        self.rootLogger.addHandler(self.__streamHandler)
        
        self.rootLogger.debug("Logger initialized")
        atexit.register(self.__cleanup)
        
        # controls if detail log will be available after program exit
        self.__detaillog_enabled = False
        self.__detaillog_name    = self.__addTmpFileHandler()
        
        if args.verbose: self.enableDetailLog()
        
    def __addTmpFileHandler(self):
        formatter   = logging.Formatter('[%(asctime)s:%(msecs)d] %(levelname)s\t%(message)s (%(name)s)','%Y:%m:%d:%H:%M:%S')
        _, name     = tempfile.mkstemp(prefix='%s.'%self.__name, suffix='.log')
        fileHandler = logging.FileHandler(name)
        fileHandler.setFormatter(formatter)
        fileHandler.setLevel(logging.DEBUG)
        self.rootLogger.addHandler(fileHandler)
        logger.debug("Temporary file logging enabled '%s'" % name)
        return name
    
    def printDetailedLogInfo(self):
        sys.stdout.write("*** complete log message is stored at '%s' ***\n" % self.__detaillog_name)
    
    def enableDetailLog(self):
        self.__detaillog_enabled = True
        
    def __cleanup(self):
        if not self.__detaillog_enabled and self.__detaillog_name:
            logger.debug("Cleaning temporary log message '%s'" % self.__detaillog_name)
            os.remove(self.__detaillog_name)
        else:
            self.printDetailedLogInfo()
        pass


