import logging
from logging import Formatter
import inspect
import sys
from copy import deepcopy
import logging
logger = logging.getLogger(__name__)

class ExtendedFormatter(Formatter):
    def __init__(self, fmt=None, datefmt=None, useColor=False, useIdents=False):
        self.usesColor = useColor
        self.useIdents = useIdents
        self.minIdent  = sys.maxint
        super(ExtendedFormatter, self).__init__(fmt, datefmt)
        
    def format(self, record):
        record = deepcopy(record)
        if self.usesColor:
            color_end = '\033[00m'
            try:
                color_begin= {
                     logging.DEBUG    : '',
                     logging.INFO     : '\033[01;32m',
                     logging.WARNING  : '\033[01;33m',
                     logging.ERROR    : '\033[01;31m',
                     logging.CRITICAL : '\033[01;31m',
                     logging.FATAL    : '\033[00;31m'
                    }[record.levelno]
            except:
                color_begin = ''
                color_end = ''
                
            record.levelname = color_begin+'*'+color_end
            
            #record.levelno == logging.ERROR or 
            if record.levelno == logging.CRITICAL or record.levelno == logging.FATAL:
                record.msg = color_begin+record.msg+color_end
        if self.useIdents:
            ident = len(inspect.stack())
            if ident<self.minIdent:
                self.minIdent = ident
            record.msg=' '*(ident-self.minIdent)+record.msg
        return Formatter.format(self, record)