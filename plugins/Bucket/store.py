#!/usr/bin/env python3
'''
The core bucket bot store.
'''
import os
import re
from string import Template
import random
import sqlite3

# an RE matching $kind or ${kind} 
kind_re = re.compile("[$][{]?([^ 0-9]\w+)[}]?")

class RandomTerm:
    '''
    A thing that acts like a random term string of a given kind.
    '''
    def __init__(self, bs, kind):
        self.bs = bs
        self.kind = kind
    def __str__(self):
        return self.bs.choose(self.kind)

class RandomHeld:
    '''
    A thing that acts like a random held item.
    '''
    def __init__(self, bs):
        self.bs = bs
    def __str__(self):
        held = self.bs.held_items()
        return random.choice(held)

class RandomGive:
    '''
    A thing that acts like a random held item but will remove the chosen.
    '''
    def __init__(self, bs):
        self.bs = bs
    def __str__(self):
        held = self.bs.held_items()
        item = random.choice(held)
        self.bs.drop_item(item)
        return item

class RandomTake:
    '''
    A thing that acts like random old item but will add to inventory
    '''
    def __init__(self, bs):
        self.bs = bs
    def __str__(self):
        item = self.bs.choose("item")
        self.bs.give_item(item)
        return item
    

class Bucket:
    'The dumbest smart container around'

    def __init__(self, filename):
        self.db = sqlite3.connect(filename)
        cur = self.db.cursor()
        
        # A term is text of a certain kind.  The kind is a free-form
        # word but some are reserved.  An "item" kind is something the
        # bot holds or has held, a factoid is a triplet of a
        # "subject", a "link" and a "tidbit" kind.  Other kinds are
        # used to allow mad lib substitution in text

        cur.execute("""
CREATE TABLE IF NOT EXISTS terms (
id INTEGER PRIMARY KEY AUTOINCREMENT,
kind TEXT NOT NULL,
text TEXT NOT NULL,
UNIQUE(kind, text))""")

        # facts
        cur.execute("""
CREATE TABLE IF NOT EXISTS facts (
id INTEGER PRIMARY KEY AUTOINCREMENT,
subject_id INTEGER NOT NULL,
link_id INTEGER NOT NULL,
tidbit_id INTEGER NOT NULL,
UNIQUE(subject_id, link_id, tidbit_id)
)""")

        # Currently holding these items, item_id points to a value.
        cur.execute("""
CREATE TABLE IF NOT EXISTS holding (
id INTEGER PRIMARY KEY AUTOINCREMENT,
item_id INTEGER NOT NULL,
UNIQUE(item_id)
)""")

        self.db.commit()

    def term(self, text, kind):
        '''
        Return term ID, creating it if novel.
        '''
        cur = self.db.cursor()
        got = cur.execute("SELECT id FROM terms WHERE kind=? AND text=?",
                          (kind, text)).fetchone()
        if got:
            print ("OLD TERM ID:",got[0])
            return got[0]

        cur.execute("INSERT INTO terms(kind,text) VALUES(?,?)",
                    (kind, text))
        self.db.commit()
        tid = cur.lastrowid
        print("NEW TERM ID:", tid)
        
    def choose(self, kind):
        '''
        Return a random term of kind
        '''
        cur = self.db.cursor()
        got = cur.execute("""SELECT text FROM terms
        WHERE kind=? ORDER BY RANDOM() LIMIT 1""",(kind,))
        return got.fetchone()[0]
        
    def system_kinds(self):
        return set("olditem newitem giveitem".split())

    def known_kinds(self):
        '''
        Return a set of known kinds.  

        These are as defined in terms.kind plus some "system" kinds.
        '''
        cur = self.db.cursor()
        got = cur.execute("SELECT DISTINCT kind FROM terms")
        s = set([one[0] for one in got.fetchall()])
        return s.union(self.system_kinds())

    def num_kind(self, kind='item'):
        cur = self.db.cursor()
        got = cur.execute("SELECT count(*) FROM terms WHERE kind=?",
                          (kind,))
        return got.fetchone()[0]
            

    def resolve(self, text):
        '''
        Return text after resolving any $var.
        '''
        kinds = set(re.findall(kind_re, text))
        if not kinds:
            return text

        # Any unknown $vars are left literal
        diff = kinds.intersection(self.known_kinds())
        if not diff:
            return text

        data = dict()

        # special handling.  
        if 'item' in kinds:      # OG Bucket used "$item" 
            kinds.remove('item') # to mean held item.
            data['item'] = RandomHeld(self)
        if 'olditem' in kinds:   # We mean item as previously held.
            kinds.remove('olditem') # Introduce $olditem
            data['olditem'] = RandomTerm(self, 'item')
        if 'giveitem' in kinds:  # held item, removed
            kinds.remove('giveitem')
            data['giveitem'] = RandomGive(self)
        if 'newitem' in kinds:   # re take a previously held
            kinds.remove('newitem')
            data['newitem'] = RandomTake(self)

        # rest are simple lookups
        for kind in kinds:
            data[kind] = RandomTerm(self, kind)

        t = Template(text)
        text = t.safe_substitute(**data)

        # Iterate until all known kinds of vars are resolved.
        return self.resolve(text)


    def factoid(self, subject, link, tidbit):
        '''
        Return factoid ID, creating it if novel.
        '''
        sid = self.term(subject, "subject")
        lid = self.term(link, "link")
        tid = self.term(tidbit, "tidbit")

        cur = self.db.cursor()
        got = cur.execute("""SELECT id FROM facts 
        WHERE subject_id=? AND link_id=? AND tidbit_id=?""",
                          (sid, lid, tid)).fetchone()
        if got:
            return got[0]
        cur.execute("""INSERT INTO facts(subject_id, link_id, tidbit_id)
        VALUES(?,?,?)""", (sid, lid, tid))
        self.db.commit()
        return cur.lastrowid

    ### Items interface.  The store may "hold" a number of items and
    ### any item ever held is remembered.

    def give_item(self, item):
        '''
        Give an item to hold, return its ID.
        '''
        iid = self.term(item, "item")
        cur = self.db.cursor()
        cur.execute("INSERT OR IGNORE INTO holding(item_id) VALUES(?)", (iid,))
        self.db.commit()
        return iid

    def drop_item(self, item):
        '''
        Bot will no longer hold item.
        '''
        cur = self.db.cursor()
        cur.execute("""DELETE FROM holding WHERE item_id in 
        ( SELECT id FROM terms 
          WHERE terms.kind='item' AND terms.text=? )""",
                    (item,))
        self.db.commit()

    def held_items(self):
        '''
        Return list of items currently held ordere oldest to newest.
        '''
        cur = self.db.cursor()
        got = cur.execute("""SELECT text FROM terms
        INNER JOIN holding on terms.id = holding.item_id
        ORDER BY holding.id""")
        if not got:
            return []
        return [one[0] for one in got.fetchall()]
        
    def drop_item_at(self, item, index):
        '''
        Drop the item at index in held list. 
        '''
        # fixme: probably not the most optimal...
        held = self.held_items();
        self.drop_item(held[index])
        

if '__main__' == __name__:
    import sys
    filename = sys.argv[1]
    b = Bucket(filename)
    
    command = sys.argv[2]
    c = getattr(b, command)
    r = c(*sys.argv[3:])
    print(r)
    
