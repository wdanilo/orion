from weakref import ref
import inspect
import sys

class Event(object):
    def __init__(self, *args, **kwargs):
        self.args = args
        for key, val in kwargs.items():
            setattr(self, key, val)
    
    def __str__(self):
        return 'Event '+str(self.__dict__)


class Signal(object):
    def __init__(self):
        stack = inspect.stack()
        frame = stack[1][0]
        flocals = frame.f_locals
        caller = flocals.get('self', None)
        if not caller:
            modname = flocals.get('__name__', None)
            if modname: caller = sys.modules[modname]
        self.__target = caller
    
        self.slots = []
        self.blocked = False #to prevent looped Signals

        # for keeping references to _WeakMethod_FuncHost objects.
        # If we didn't, then the weak references would die for
        # non-method slots that we've created.
        self.funchost = []

    def __call__(self, *args, **kwargs):
        if not self.blocked:
            baseEvent = kwargs.pop('event',None)
            if baseEvent:
                vardict = vars(baseEvent)
                vardict.update(kwargs)
            else:
                vardict = kwargs
            event = Event(*args, target=self.__target, **vardict)
            self.chainCall(event)
                
    def call(self, *args, **kwargs):
        self.__call__(*args, **kwargs)
        
    def chainCall(self, event):
        if not self.blocked:
            self.blocked = True
            for i in range(len(self.slots)):
                slot = self.slots[i]
                if slot != None:
                    event.currentTarget = self.__target
                    slot(event)
                else:
                    del self.slots[i]
            self.blocked = False
    
    def connect(self, slot):
        self.disconnect(slot)
        if inspect.ismethod(slot):
            self.slots.append(WeakMethod(slot))
        else:
            o = _WeakMethod_FuncHost(slot)
            if isinstance(slot, Signal):
                wref = WeakChainMethod(o.func)
            else:
                wref = WeakMethod(o.func)
            self.slots.append(wref)
            # we stick a copy in here just to keep the instance alive
            self.funchost.append(o)

    def disconnect(self, slot):
        try:
            for i in range(len(self.slots)):
                wm = self.slots[i]
                if inspect.ismethod(slot):
                    if wm.f == slot.im_func and wm.c() == slot.im_self:
                        del self.slots[i]
                        return
                else:
                    if wm.c().hostedFunction == slot:
                        del self.slots[i]
                        return
        except:
            pass

    def disconnectAll(self):
        del self.slots
        del self.funchost
        self.slots = []
        self.funchost = []

class _WeakMethod_FuncHost:
    def __init__(self, func):
        self.hostedFunction = func
    def func(self, *args, **kwargs):
        self.hostedFunction(*args, **kwargs)

# this class was generously donated by a poster on ASPN (aspn.activestate.com)
class WeakMethod:
    def __init__(self, f):
        self.f = f.im_func
        self.c = ref(f.im_self)
    def __call__(self, *args, **kwargs):
        if self.c() == None : return
        self.f(self.c(), *args, **kwargs)
        
class WeakChainMethod(WeakMethod):
    def __call__(self, event):
        self.c().hostedFunction.chainCall(event)
        
        
        
'''
class SignalGroup(Signal):
    def __init__(self, *names):
        Signal.__init__(self)
        self.__signals = {}
        
        self.q = {}
        for name in names:
            if name not in self.__signals:
                signal = Signal()
                self.__signals[name] = signal
                self.q[signal] = True
                setattr(self, name, signal)
                self.connect(signal)
                signal.connect(self)
    
    def chainCall(self, event):
        if event.currentTarget == self:
            Signal.chainCall(self, event)
        
    def connect_by_name(self, dst):
        assert isinstance(dst, SignalGroup)
        for name, signal in self.__signals.iteritems():
            try:
                dst_signal = dst[name]
            except: continue
            signal.connect(dst_signal)
    
    def __getitem__(self, key):
        return self.__signals[key]
   
def f(e):
    print 'f!'
    
def g(e):
    print 'g!'
    
    
a = SignalGroup('x', 'y', 'z')
b = SignalGroup('x', 'y', 'z')

a.x.connect(b)
b.connect(f)
#todo
a()
        
   '''     