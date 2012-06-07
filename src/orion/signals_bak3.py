from weakref import ref
import inspect

class Event(object):
    def __init__(self, *args, **kwargs):
        self.__kwargs = kwargs
        self.__args = args
            
    def __getattr__(self, name):
        return self.__kwargs[name]
    
    @property
    def args(self):
        return self.__args
    
    def copy(self):
        return Event(*self.args, **self.__kwargs)
    
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

    def __call__(self, target, *args, **kwargs):
        baseEvent = kwargs.pop('event',None)
        if baseEvent:
            vardict = vars(baseEvent)
            vardict.update(kwargs)
        else:
            vardict = kwargs
        event = Event(*args, target=target, currentTarget=target, **vardict)
        self._call(event)

    def chainCall(self, target, event):
        event.currentTarget = target
        self._call(event)
    
    def _call(self, event):
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
                wref = WeakChainMethod(self, o.func)
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
    def __init__(self, target, f):
        self.target = target
        WeakMethod.__init__(self, f)
    def __call__(self, event):
        self.c().hostedFunction.chainCall(self.target, event.copy())
 
 
class SignalGroup(Signal):
    def __init__(self, *names):
        Signal.__init__(self)
        self.__signal_names = {}
        self.__signals = {}
        for name in names:
            if name not in self.__signal_names:
                signal = Signal()
                self.__signal_names[name] = signal
                self.__signals[signal] = True
                setattr(self, name, signal)
                signal.connect(self)
                
    def _call(self, event):
        if not self.blocked:
            self.blocked = True
            if not event.currentTarget in self.__signals:
                for slot in self.__signals:
                    slot.chainCall(self, event)
            for i in range(len(self.slots)):
                slot = self.slots[i]
                if slot != None:
                    slot(event)
                else:
                    del self.slots[i]
            self.blocked = False
    
    def connect_by_name(self, dst):
        assert isinstance(dst, SignalGroup)
        for name, signal in self.__signal_names.iteritems():
            try:
                dst_signal = dst[name]
            except: continue
            signal.connect(dst_signal)
    
    def __getitem__(self, key):
        return self.__signal_names[key]
    
a = Signal()

events =[]
for x in range(0,1000):
    s = Signal()
    events.append(s)
    a.connect(s)
print 'done'
