import os
from orion.core.comm import ipc

def findSockfile (display=None, prefix=''):
    """
        Finds the appropriate socket file.
    """
    cache_directory = os.path.expandvars('$XDG_CACHE_HOME')
    if cache_directory == '$XDG_CACHE_HOME': #if variable wasn't set
        cache_directory = os.path.expanduser("~/.cache")
    return os.path.join(cache_directory, '%s.%s'%(prefix,display))


class Server(ipc.Server):
    def __init__(self, fname, wmcore):
        ipc.Server.__init__(self, fname, self.call)
        self.wmcore = wmcore

    def call(self, data):
        selectors, name, args, kwargs = data
        try:
            obj = self.qtile.select(selectors)
        except Exception, e:
            print 'TODO'
            raise e
        cmd = obj.command(name)
        if not cmd:
            #no such command
            print 'TODO'
            raise e
        try:
            return SUCCESS, cmd(*args, **kwargs)
        except CommandError, v:
            return ERROR, v.args[0]
        except Exception, v:
            return EXCEPTION, traceback.format_exc()
        self.wmcore.conn.flush()