from collections import OrderedDict

class enum(object):
    def __init__(self, *sequential, **named):
        self.__enums = OrderedDict(zip(sequential, range(len(sequential))), **named)
        for key, val in self.__enums.items():
            setattr(self, key, val)
    
    def __getitem__(self, key):
        return self.__enums[key]
    
    def items(self):
        return self.__enums.items()
    
    def keys(self):
        return self.__enums.keys()
    
    def values(self):
        return self.__enums.values()
    
    def __iter__(self):
        return self.__enums.__iter__()
        
class flagEnum(object):
    
    def __init__(self, *sequential):
        val = 1
        self.__enums = OrderedDict()
        for el in sequential:
            self.__enums[el] = val
            setattr(self, el, val)
            val = val << 1
    
    def __getitem__(self, key):
        return self.__enums[key]
    
    def items(self):
        return self.__enums.items()
    
    def keys(self):
        return self.__enums.keys()
    
    def values(self):
        return self.__enums.values()
    
    def __iter__(self):
        return self.__enums.__iter__()


def chrArr(arr):
    return ''.join([chr(i) for i in arr])

def pack(**kwargs):
    return type('Pack', (), kwargs)

#############################################


import operator, functools, os
#import xcbq

def lget(o, v):
    try:
        return o[v]
    except (IndexError, TypeError):
        return None


def translateMasks(modifiers):
    """
        Translate a modifier mask specified as a list of strings into an or-ed 
        bit representation.
    """
    masks = []
    for i in modifiers:
        try:
            raise # to jest do przenesienia gdzie indziej - petla importow z proto
            #masks.append(proto.ModMasks[i])
        except KeyError:
            raise KeyError("Unknown modifier: %s"%i)
    return reduce(operator.or_, masks) if masks else 0


def shuffleUp(lst):
    if len(lst) > 1:
        c = lst[-1]
        lst.remove(c)
        lst.insert(0, c)


def shuffleDown(lst):
    if len(lst) > 1:
        c = lst[0]
        lst.remove(c)
        lst.append(c)


class LRUCache:
    """
        A decorator that implements a self-expiring LRU cache for class
        methods (not functions!).

        Cache data is tracked as attributes on the object itself. There is
        therefore a separate cache for each object instance.
    """
    def __init__(self, size=100):
        self.size = size

    def __call__(self, f):
        cacheName = "_cached_%s"%f.__name__
        cacheListName = "_cachelist_%s"%f.__name__
        size = self.size

        @functools.wraps(f)
        def wrap(self, *args):
            if not hasattr(self, cacheName):
                setattr(self, cacheName, {})
                setattr(self, cacheListName, [])
            cache = getattr(self, cacheName)
            cacheList = getattr(self, cacheListName)
            if cache.has_key(args):
                cacheList.remove(args)
                cacheList.insert(0, args)
                return cache[args]
            else:
                ret = f(self, *args)
                cacheList.insert(0, args)
                cache[args] = ret
                if len(cacheList) > size:
                    d = cacheList.pop()
                    cache.pop(d)
                return ret
        return wrap


def isStringLike(anobj):
    try:
        # Avoid succeeding expensively if anobj is large.
        anobj[:0]+''
    except:
        return 0
    else:
        return 1


def isSequenceLike(anobj):
    """
        Is anobj a non-string sequence type (list, tuple, iterator, or
        similar)?  Crude, but mostly effective.
    """
    if not hasattr(anobj, "next"):
        if isStringLike(anobj):
            return 0
        try:
            anobj[:0]
        except:
            return 0
    return 1


def rgb(x):
    """
        Returns a valid RGBA tuple.

        Here are some valid specifcations:
            #ff0000
            ff0000
            with alpha: ff0000.5  
            (255, 0, 0)
            (255, 0, 0, 0.5)
    """
    if isinstance(x, tuple) or isinstance(x, list):
        if len(x) == 4:
            alpha = x[3]
        else:
            alpha = 1
        return (x[0]/255.0, x[1]/255.0, x[2]/255.0, alpha)
    elif isinstance(x, basestring):
        if x.startswith("#"):
            x = x[1:]
        if "." in x:
            x, alpha = x.split(".")
            alpha = float("0."+alpha)
        else:
            alpha = 1
        if len(x) != 6:
            raise ValueError("RGB specifier must be 6 characters long.")
        vals = [int(i, 16) for i in (x[0:2], x[2:4], x[4:6])]
        vals.append(alpha)
        return rgb(vals)
    raise ValueError("Invalid RGB specifier.")


class Data:
    def __init__(self, name):
        m = __import__(name)
        dirname, _ = os.path.split(m.__file__)
        self.dirname = os.path.abspath(dirname)

    def path(self, path):
        """
            Returns a path to the package data housed at 'path' under this
            module.Path can be a path to a file, or to a directory.

            This function will raise ValueError if the path does not exist.
        """
        fullpath = os.path.join(self.dirname, path)
        if not os.path.exists(fullpath):
            raise ValueError, "dataPath: %s does not exist."%fullpath
        return fullpath

data = Data(__name__)


def scrub_to_utf8(text):
    if not text:
        return ""
    elif isinstance(text, unicode):
        return text
    else:
        try:
            return text.decode("utf-8")
        except UnicodeDecodeError:
            # We don't know the provenance of this string - so we scrub it to ASCII.
            return "".join(i for i in text if 31 < ord(i) <  127)


