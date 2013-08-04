#!/usr/bin/env python

import bag
import os, shelve

def test_basics():
    b = bag.Bag(a=1, b=[2,3], c='a={a}, b={b}')
    p = b.pick(resolve=False)
    assert p['a'] == 1 and p['b'] in [2,3] and p['c'] == 'a={a}, b={b}', str(p)
    f = b.pick()
    assert f['a'] == '1' and f['b'] in ['2','3'] \
        and (f['c'] == 'a=1, b=2' or f['c'] == 'a=1, b=3'), str(f)

def test_dict():
    b = bag.Bag(a=1, b=[2,3], c='a={a}, b={b}')    
    assert b['a'] == '1'
    assert b['b'] in ['2','3'], str(b)
    b['d'] = 'one'
    b['d'] = 'two'
    assert len(b.get_all('d')) == 2
    
def test_store():
    filename = 'test_bag.shelf'
    if os.path.exists(filename):
        os.remove(filename)
    db = shelve.open(filename, writeback=True)
    print 'shelve returns (%s) %s' % (type(db), db)
    b = bag.Bag(store=db, a=1, b=[2,3], c='a={a}, b={b}')        
    assert os.path.exists(filename)
    print 'db:',str( db)
    assert db['a'] == set([1])
    print 'Got %d items in store' % len(db)
    b.add('d','dee')
    assert b.get_all('d') == set(['dee'])
    b.add('d','two')
    assert b.get_all('d') == set(['dee','two'])
    b2 = bag.Bag(store=db)
    print str(b2)
    assert b2['a'] == '1'
    assert b2['b'] in ['2','3'], str(b2)
    assert len(b2.get_all('b')) == 2, str(b2.get_all('b'))
    print b2.get_all('b')

def test_format():
    b = bag.Bag(verb=['run','jump'], tobe='to {verb} or not to {verb}')
    print b['tobe']

if '__main__' == __name__:
    test_basics()
    test_dict()
    test_store()
    test_format()
