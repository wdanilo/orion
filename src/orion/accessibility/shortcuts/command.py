import inspect

class Command(object):
    class _Attrib(object):
        def __init__(self, name):
            self.name = name
        def eval(self, obj):
            return getattr(obj, self.name)
        
    class _Method(object):
        def __init__(self, *args, **kwargs):
            self.__args = args
            self.__kwargs = kwargs
        def eval(self, obj):
            return obj(*self.__args, **self.__kwargs)
        
    class _Body(object):
        def __init__(self, startname, cmd_locals={}, cmd_globals={}):
            self.__startname = startname
            self.__locals = cmd_locals
            self.__globals = cmd_globals
            self.__chain = []
        def __getattr__(self, name):
            self.__chain.append(Command._Attrib(name))
            return self
        def __call__(self, *args, **kwargs):
            self.__chain.append(Command._Method(*args, **kwargs))
            return self
        def eval(self):
            try:
                obj = self.__locals[self.__startname]
            except:
                obj = self.__globals[self.__startname]
            for op in self.__chain:
                obj = op.eval(obj)
            return obj
                
    def __getattr__(self, name):
        stack = inspect.stack()
        cmd_locals = stack[1][0].f_locals
        cmd_globals = stack[1][0].f_globals
        return Command._Body(name, cmd_locals=cmd_locals, cmd_globals=cmd_globals)

