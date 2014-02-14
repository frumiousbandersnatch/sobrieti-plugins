#!/usr/bin/env python

import os
import UserDict

def load(subname, timestamp=None, datadir = "$HOME/btsync/flair"):
    filename = os.path.expandvars(os.path.join(datadir, subname))
    st = os.stat(filename)
    if st.st_size == 0:
        return

    if timestamp and st.st_mtime <= timestamp:
        return

    dat = dict()
    #print 'loading',filename
    with open(filename) as fp:
        for line in fp.readlines():
            redditor, days = line.strip().split(',')
            days = int(days.split()[0])
            dat[redditor] = days
    return (st.st_mtime, subname, dat)

class Flair(UserDict.DictMixin):
    def __init__(self, subname, datadir = "$HOME/btsync/flair"):
        self.subname = subname
        self.datadir = datadir
        self.timestamp = None
        self.dat = dict()
        self.reload()
    def keys(self):
        self.reload()
        return self.dat.keys()

    def __getitem__(self, name):
        self.reload()
        return self.dat[name]

    def reload(self):
        ret = load(self.subname, self.timestamp, self.datadir)
        if not ret:
            return
        self.timestamp, _, self.dat = ret



if '__main__' == __name__:
    import sys
    from time import time
    t0 = time()
    f = Flair(sys.argv[1])
    t1 = time()
    assert f.keys()
    t2 = time()
    count1 = 0
    for redditor, days in f.items():
        count1 += days
    t3 = time()
    count2 = 0
    for redditor, days in f.items():
        count2 += days
    t4 = time()
    assert count1
    assert count1 == count2
    print t1-t0, t2-t1, t3-t2, t4-t3

