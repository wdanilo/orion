#!/usr/bin/python
import os
import sys

import inspect
class FileTracer(object):
    stdout = None
    enabled = False
    flushed = True
    traceNumber = 0
    
    @staticmethod
    def enable():
        if not FileTracer.enabled:
            FileTracer.enabled = True
            FileTracer.stdout = sys.stdout
            sys.stdout = FileTracer
    
    @staticmethod
    def disable():
        if FileTracer.enabled:
            FileTracer.enabled = False
            sys.stdout = FileTracer.stdout
            
    @staticmethod
    def write(s):
        curframe = inspect.currentframe()
        calframe = inspect.getouterframes(curframe, 2)
        if s == '\n' and not FileTracer.flushed:
            FileTracer.flushed = True
            path = calframe[1][1]
            name = os.path.basename(path)
            if name == '__init__.py':
                name = os.path.basename(os.path.dirname(path))+'/'+name
            s = ' (%s: %s, traceno: %s)\n'%(calframe[1][2], name, FileTracer.traceNumber)
            FileTracer.traceNumber += 1
        else:
            FileTracer.flushed = False
        FileTracer.stdout.write(s)
    
    
    
if __name__ == '__main__':
    FileTracer.enable()
    
    # update environment variables
    env        = []
    installdir = os.path.dirname(__file__)
    plugdir    = os.path.join(installdir, 'plugins')
    homedir    = os.path.expanduser('~')
    env.append(plugdir)
    env.append(os.path.join(homedir,'.orion','plugins'))
    try:
        env.append(os.environ['ORION_PLUGIN_PATH'].split(os.pathsep))
    except:
        pass
    os.environ['ORION_PLUGIN_PATH'] = os.pathsep.join(env)
    paths=['/home/wdanilo/dev/python/orion/plugins']
    sys.path.append(os.path.join(installdir,'src'))
    
    # run orion
    import orion
    print orion
    orion.run()