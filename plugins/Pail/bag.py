#!/usr/bin/env python
'''

'''

import random

def stringify(thing, **kwds):
    if isinstance(thing, basestring):
        return thing.format(**kwds)
    return str(thing)

def resolve_format(dat, formatter = stringify, **extra):
    kwds = dict(extra)
    unformatted = dict(dat)
    formatted = dict()

    while unformatted:
        changed = False
        for k,v in unformatted.items():
            try:
                new_v = formatter(v, **kwds)
            except KeyError:
                continue        # maybe next time
            changed = True
            formatted[k] = new_v
            kwds[k] = new_v
            unformatted.pop(k)
            continue
        if not changed:
            break
        continue
    if unformatted:
        formatted.update(unformatted)
    return formatted
    

import UserDict
class Bag(UserDict.DictMixin):
    def __init__(self, store=None, **kwds):
        if store is None: 
            store = dict()
        self._bag = store
        for k,v in kwds.items():
            self.add(k,v)
        self.sync()

    def sync(self):
        if hasattr(self._bag,'sync'):
            self._bag.sync()

    def keys(self):
        return self._bag.keys()

    def __getitem__(self, name):
        return self.pick()[name]

    def __setitem__(self, name, value):
        self.add(name, value)

    def __delitem__(self, name):
        self.purge(name)

    def pick(self, resolve = True):
        '''
        Return a selection of the bags contents
        '''
        ret = dict()
        for k,v in self._bag.items():
            ret[k] = random.choice(list(v))
        if resolve:
            ret = resolve_format(ret)
        return ret

    def add(self, name, value):
        if name not in self._bag.keys():
            self._bag[name] = set()
        if not (isinstance(value, list) or isinstance(value, set)):
            value = set([value])
        else:
            value = set(value)
        self._bag[name] |= value
        print self._bag[name],value
        self.sync()

    def get_all(self, name):
        self._bag.setdefault(name, set())
        return self._bag[name]

    def purge(self, name):
        del(self._bag[name])
        self.sync()

    def remove(self, name, regex):
        val = self._bag.get(name)
        if not val: 
            return
        p = re.compile(regex)
        val = set([x for x in val if not p.match(x)])
        self._bag[name] = val
        self.sync()

            
                
def main(*args):
    import shelve
    db = shelve.open(args[0])
    b = Bag(store=db)
    if args[1] == 'dump':
        for k in b.keys():
            print k,b.get_all(k)
    if args[1] == 'add':
        b.add(args[2], args[3])


if '__main__' == __name__:
    import sys
    main(*sys.argv[1:])
