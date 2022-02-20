#!/usr/bin/env python3
'''
The core bucket bot store.
'''
import os
import re
from string import Template
import random
import sqlite3

from . import prime


# an RE matching $kind or ${kind} 
kind_re = re.compile(r"[$][{]?([^ 0-9]\w+)[}]?")

# Need also to support: $who, $someone, $inventory (list items)
class RandomTerm:
    '''
    A thing that acts like a random term string of a given kind.
    '''
    def __init__(self, bs, kind):
        self.bs = bs
        self.kind = kind
    def __str__(self):
        text = self.bs.choose_term(self.kind)
        if not text:
            return self.kind
        return text


class RandomHeld:
    '''
    A thing that acts like a random held item.
    '''
    def __init__(self, bs, kind='held'):
        self.bs = bs
        self.kind = kind
    def __str__(self):
        held = self.bs.held_items()
        if not held:
            return self.kind
        return random.choice(held)


class RandomGive:
    '''
    A thing that acts like a random held item but will remove the
    chosen.

    Note, there is no underflow protection.  If used when not holding
    anything it will simply return the kind.
    '''
    def __init__(self, bs, kind='give'):
        self.bs = bs
        self.kind = kind
    def __str__(self):
        held = self.bs.held_items()
        if not held:
            return self.kind
        item = random.choice(held)
        self.bs.drop_item(item)
        return item


class RandomTake:
    '''
    A thing that acts like random old item but will add to inventory

    Note this does not overflow protection.
    '''
    def __init__(self, bs, kind='take'):
        self.bs = bs
        self.kind = kind
    def __str__(self):
        item = self.bs.choose_term("item")
        if not item:
            return self.kind
        self.bs.give_item(item)
        return item
    

class Bucket:
    'The dumbest smart container around'

    system_nick = ":system:"

    def __init__(self, dbname=":memory:"):
        self.db = prime.init(dbname)

        for subject, lts in prime.system_facts.items():
            for link, tidbit in lts:
                self.factoid(subject, link, tidbit,
                             commit=False, creator=self.system_nick)
        self.db.commit()

    def idterm(self, tid):
        '''
        Return the term (kind,text) for the term ID.
        '''
        cur = self.db.cursor()
        got = cur.execute("SELECT kind,text FROM terms WHERE id=?", (tid,))
        return got.fetchone()

    def term(self, text, kind, commit=True, creator=""):
        '''
        Return term ID, creating it if novel.

        Pass commit=False to batch up calls and do a single explicit
        commit for much greater speed. 
        '''
        cur = self.db.cursor()
        got = cur.execute("SELECT id FROM terms WHERE kind=? AND text=?",
                          (kind, text)).fetchone()
        if got:
            #print ("OLD TERM ID:",got[0])
            return got[0]

        cur.execute("""
        INSERT INTO terms(kind,text,created_by) VALUES(?,?,?)""",
                    (kind, text, creator))
        if commit:
            self.db.commit()
        tid = cur.lastrowid
        #print("NEW TERM ID:", tid)
        return tid
        
    def terms(self, kind, return_ids=False):
        '''
        Return list of term texts of given kind
        '''
        cur = self.db.cursor()
        got = cur.execute("SELECT text,id FROM terms WHERE kind=? ORDER BY id",
                          (kind, )).fetchall()
        if return_ids:
            return got
        return [one[0] for one in got]

    def choose_term(self, kind):
        '''
        Return a random term of kind
        '''
        cur = self.db.cursor()
        got = cur.execute("""SELECT text FROM terms
        WHERE kind=? ORDER BY RANDOM() LIMIT 1""",(kind,)).fetchone()
        if not got:
            raise KeyError(f'no terms of kind "{kind}"')
        return got[0]       # singlets returned from db as (s,)
        
    def system_kinds(self):
        '''
        Return reserved system kinds of terms.

        Some have side effects (held, give, take).

        Others are from irc (who, to, op, someone).
        '''
        return set("subject link factoid item held give take who someone to op".split())

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
            

    def resolve(self, text, **more):
        '''
        Return text after resolving any $var.

        The "more" keywords arg passes more string like objects for
        the resolution.  In particular, these are often used:

        - who :: nick of initiator of the resolve
        - someone :: a recently active nick
        - to :: the intended recipient, usually the bot
        - op :: a recently active channel operator

        '''
        kinds = set(re.findall(kind_re, text))
        if not kinds:
            return text

        data = dict()

        # Handling of system kinds.  
        if 'held' in kinds:
            kinds.remove('held')
            data['held'] = RandomHeld(self)
        if 'give' in kinds:  # held item, removed
            kinds.remove('give')
            data['give'] = RandomGive(self)
        if 'take' in kinds:   # re take a previously held
            kinds.remove('take')
            data['take'] = RandomTake(self)

        # rest are simple lookups
        for kind in kinds:
            data[kind] = RandomTerm(self, kind)

        data.update(more)

        t = Template(text)
        new_text = t.safe_substitute(**data)
        if text == new_text:
            return text

        # Iterate until all known kinds of vars are resolved.
        return self.resolve(new_text, **more)

    def purge_term(self, text, kind):
        '''
        Purge a term.
        '''
        self.sql("DELETE FROM terms where kind=? and text=?",
                 (kind, text))
    ### Fact interface.
    # The label "factoid" implies a triplet: (subject, link, tidbit)

    def idfactoid(self, fid):
        '''
        Return the factoid (subject,link,tidbit) for the factoid ID.
        '''
        return self.sql("""
        SELECT subject.text, link.text, tidbit.text
        FROM facts fact
        LEFT JOIN terms subject ON subject.id = fact.subject_id
        LEFT JOIN terms link    ON link.id    = fact.link_id
        LEFT JOIN terms tidbit  ON tidbit.id  = fact.tidbit_id
        WHERE fact.id=?""", (fid,)).fetchone()

    def factoidid(self, factoid):
        '''
        Return the ID of the factoid (subject,link,tidbit) or None.
        '''
        got = self.sql("""
        SELECT fact.id
        FROM facts fact
        LEFT JOIN terms subject ON subject.id = fact.subject_id
        LEFT JOIN terms link    ON link.id    = fact.link_id
        LEFT JOIN terms tidbit  ON tidbit.id  = fact.tidbit_id
        WHERE subject.text=? and link.text=? and tidbit.text=?""", factoid)
        if got:
            return got.fetchone()[0]
        return

    def factoid(self, subject, link, tidbit, commit=True, creator=""):
        '''
        Return pair (int, bool) giving factoid ID and if it was
        created anew.
        '''
        sid = self.term(subject, "subject", commit, creator)
        lid = self.term(link, "link", commit, creator)
        tid = self.term(tidbit, "tidbit", commit, creator)

        cur = self.db.cursor()
        got = cur.execute("""SELECT id FROM facts 
        WHERE subject_id=? AND link_id=? AND tidbit_id=?""",
                          (sid, lid, tid)).fetchone()
        if got:
            return (got[0], False)
        cur.execute("""
        INSERT INTO facts(subject_id, link_id, tidbit_id, created_by)
        VALUES(?,?,?,?)""", (sid, lid, tid, creator))
        if commit:
            self.db.commit()
        return (cur.lastrowid, True)

    def is_system_fact(self, subject):
        '''
        Return True if subject is for a system factoid, False if
        subject exists and is non-system, None if subject does not
        exist.
        '''
        if not isinstance(subject, str):
            subject = subject[0] # if a factoid

        got = self.sql("""
        SELECT created_by FROM terms 
        WHERE kind='subject' AND text=?
        """, (subject,)).fetchone()
        if not got:
            return None
        return got[0] == self.system_nick

    def purge_subject(self, subject):
        '''
        Purge a subject, all its facts and any orphaned tidbits.
        '''
        self.purge_term(subject, "subject")

    def purge_factoid(self, subject, link, tidbit):
        '''
        Remove a specific factoid.

        This will also purge any orphaned tidbits.
        '''
        self.sql("""
        DELETE FROM facts
        WHERE ROWID IN (
          SELECT fact.ROWID from facts fact
          LEFT JOIN terms subject ON subject.id = fact.subject_id
          LEFT JOIN terms link    ON link.id    = fact.link_id
          LEFT JOIN terms tidbit  ON tidbit.id  = fact.tidbit_id
          WHERE subject.text=? AND link.text=? AND tidbit.text=?
        )""", (subject, link, tidbit))

    def recent_factoids(self, limit=10,
                        return_facts=True, return_ids=True, creator=None):
        '''
        Return up to limit recent factoids, newest first.

        If return both factoids return as [(id, (s,l,t)), ...].

        If just ids, then [id, ...]

        If just facts then [(s,l,t], ...]

        The creator may name a creator or be '*' for all or None for
        non-system.
        '''
        if not any((return_facts, return_ids)):
            return 
                    
        if creator == "*":
            extra = ""
        elif creator is None:
            extra = f"WHERE fact.created_by != '{self.system_nick}'"
        else:
            extra = f"WHERE fact.created_by = '{creator}'"

        got = self.sql(f"""
        SELECT fact.id, subject.text, link.text, tidbit.text
        FROM facts fact
        LEFT JOIN terms subject ON subject.id = fact.subject_id
        LEFT JOIN terms link    ON link.id    = fact.link_id
        LEFT JOIN terms tidbit  ON tidbit.id  = fact.tidbit_id
        {extra}
        ORDER BY fact.created_at DESC LIMIT ?""", (limit,))
        if return_ids and return_facts:
            return [(one[0], one[1:]) for one in got.fetchall()]
        if return_ids:
            return [one[0] for one in got.fetchall()]
        return [one[1:] for one in got.fetchall()]


    def choose_factoid(self, subject=None):
        '''
        Return a random factoid as (s,l,t) triplet.

        If no subject is given, choose among all, otherwise chose
        matching.
        '''
        cur = self.db.cursor()
        if not subject:
            got = cur.execute("""SELECT subject_id, link_id, tidbit_id
            FROM facts ORDER BY RANDOM() LIMIT 1""").fetchone()
            if not got:
                raise KeyError("no facts defined")
        else:
            got = cur.execute("""SELECT subject_id, link_id, tidbit_id
            FROM facts 
            INNER JOIN terms on terms.id = subject_id
            WHERE terms.text=?
            ORDER BY RANDOM() LIMIT 1""", (subject,)).fetchone()
            if not got:
                raise KeyError(f'no facts for subject "{subject}"')

        slt = [self.idterm(tid) for tid in got]
        return tuple([one[1] for one in slt])
        
    def choose_factoid_like(self, subject, fragment):
        '''
        Return a random factoid on a subject which has fragment match.
        '''
        got = self.sql("""
        SELECT subject.text, link.text, tidbit.text
        FROM facts fact
        LEFT JOIN terms subject ON subject.id = fact.subject_id
        LEFT JOIN terms link    ON link.id    = fact.link_id
        LEFT JOIN terms tidbit  ON tidbit.id  = fact.tidbit_id
        WHERE subject.text=? and tidbit.text like ?
        ORDER BY RANDOM() LIMIT 1
        """, (subject, '%'+fragment+'%')).fetchone()
        if not got:
            raise KeyError(f'no facts for subject "{subject}" like "{fragment}"')
        return got

    def factoids(self, subject):
        '''
        Return all facts on subject as as dict {id:(triplet)}
        '''
        cur = self.db.cursor()
        got = cur.execute("""
        SELECT fact.id, link.text, tidbit.text
        FROM facts fact
        LEFT JOIN terms subject ON subject.id = fact.subject_id
        LEFT JOIN terms link    ON link.id    = fact.link_id
        LEFT JOIN terms tidbit  ON tidbit.id  = fact.tidbit_id
        WHERE subject.text=?""", (subject,)).fetchall()
        if not got:
            return dict()
        ret = dict()
        for one in got:
            ret[one[0]] = tuple([subject, one[1], one[2]])
        return ret


    ### Items interface.  The store may "hold" a number of items and
    ### any item ever held is remembered.

    def give_item(self, item, creator=""):
        '''
        Give an item to hold, return ID.
        '''
        iid = self.term(item, "item", creator=creator)
        cur = self.db.cursor()
        cur.execute("INSERT OR IGNORE INTO holding(item_id) VALUES(?)", (iid,))
        self.db.commit()
        return iid

    def sql(self, query, args=(), commit=True):
        '''
        Execute SQL query
        '''
        cur = self.db.cursor()
        got = cur.execute(query, args)
        if commit:
            self.db.commit()
        return got

    def purge_item(self, item):
        '''
        Delete item forever, drop if holding.
        '''
        self.purge_term(item, "item")

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

    def held_items(self, return_ids=False):
        '''
        Return list of items currently held ordere oldest to newest.
        '''
        cur = self.db.cursor()
        got = cur.execute("""SELECT terms.text,terms.id FROM terms
        INNER JOIN holding on terms.id = holding.item_id
        ORDER BY holding.id""")
        if not got:
            return []
        if return_ids:
            return got.fetchall()
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

    args = list()
    params = dict()
    for arg in sys.argv[3:]:
        if "=" in arg:
            k,v = arg.split("=",1)
            params[k] = v
        else:
            args.append(arg)

    sargs = ','.join([f'"{a}"' for a in args])
    skargs = ','.join([f'{k}="{v}"' for k,v in params.items()])
    print(f'{command}({sargs}, {skargs})')
    r = c(*args, **params)
    print(r)
    
