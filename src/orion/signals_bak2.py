from weakref import ref
import inspect
import sys
from copy import copy

class Event(object):
    def __init__(self, *args, **kwargs):
        self.args = args
        for key, val in kwargs.items():
            setattr(self, key, val)
    
    def __str__(self):
        return 'Event '+str(self.__dict__)


class Signal(object):
    def __init__(self):
        #self.current_target = caller
    
        self.slots = []
        self.blocked = False #to prevent looped Signals

        # for keeping references to _WeakMethod_FuncHost objects.
        # If we didn't, then the weak references would die for
        # non-method slots that we've created.
        self.funchost = []

    def __call__(self, *args, **kwargs):
        baseEvent = kwargs.pop('event',None)
        if baseEvent:
            vardict = vars(baseEvent)
            vardict.update(kwargs)
        else:
            vardict = kwargs
        
        currentTarget = self.current_target()
        target = kwargs.get('target', None)
        if not target: target = currentTarget
        event = Event(*args, target=target, currentTarget=currentTarget, **vardict)
        self.__call(event)
        
                
    def chainCall(self, event):
        event.currentTarget = self.current_target(3)
        self.__call(event)
    
    def current_target(self, offset=2):
        stack = inspect.stack()
        frame = stack[offset][0]
        flocals = frame.f_locals
        target = flocals.get('self', None)
        if not target:
            modname = flocals.get('__name__', None)
            if modname: target = sys.modules[modname]
        return target
    
    def __call(self, event):
        if not self.blocked:
            self.blocked = True
            for i in range(len(self.slots)):
                slot = self.slots[i]
                if slot != None:
                    slot(event)
                else:
                    del self.slots[i]
            self.blocked = False
    
    def __iadd__(self, slot):
        self.connect(slot)
        return self

    def __isub__(self, slot):
        self.disconnect(slot)
        return self
        
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
        self.c().hostedFunction.chainCall(copy(event))
        

'''
def f(e):
    print 'F: ',e.target, e.currentTarget
    
def g(e):
    print 'G: ',e.target, e.currentTarget
    
        
a = Signal()
b = Signal()


a += b
a += f
b += g

class A():
    def __init__(self):
        a()
x= A()
#'''
        
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
                signal.connect(self)
                self.connect(signal)
    
    def chainCall(self, event):
        currentTarget = self.current_target(3)
        if not currentTarget in self.q:
            event.currentTarget = currentTarget
            self._Signal__call(event)
            for signal in self.q:
                signal.chainCall(copy(event))
    
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

print 'a', id(a)
print 'b', id(b)

a.x.connect(b)
#a.y.connect(g)
b.connect(f)

a.x()
        
#'''     