#!/usr/bin/env python3
'''
Prime a bucket with some entries
'''

import sqlite3

system_facts = {
    "don't know": [
        ("reply", "A thousand apologies, effendi, but I do not understand."),
        ("reply", "Beeeeeeeeeeeeep!"),
        ("reply", "Can't talk, zombies!"),
        ("reply", "Error 42: Factoid not in database.  Please contact administrator of current universe."),
        ("reply", "Error at 0x08: Reference not found"),
        ("reply", "I cannot access that data."),
        ("reply", "I don't know"),
        ("reply", "I don't know anything about that."),
        ("reply", "I'm sorry, there's currently nothing associated with that keyphrase."),
        ("reply", "Not a bloody clue, sir."),
        ("reply", "UNCAUGHT EXCEPTION: TERMINATING"),
        ("action", "dumps core"),
    ],
    "band name reply": [
        ("reply", '"$band" would be a good name for a band.'),
        ("reply", '"$band" would be a nice name for a band.'),
        ("reply", '"$band" would be a nice name for a rock band.'),
        ("reply", '"$band" would make a good name for a band.'),
        ("reply", '"$band" would make a good name for a rock band.'),
        ("reply", 'That would be a good name for a band.'),
    ],
    "new fact": [
        ("reply", 'Okay, $who.'),
        ("reply", 'I am excited to learn about $subject!'),
    ],
    "existing fact": [
        ("reply", "$who, I already had it that way"),
        ("reply", "Yes, I know"),
    ],

    "duplicate item": [
        ("reply", '$who: I already have $item.'),
        ("reply", "But I've already got $item!"),
        ("reply", 'I already have $item.'),
        ("reply", "No thanks, $who, I've already got one."),
    ],

    # actions
    "drops item": [
        ("action", "fumbles and drops $give."),
    ],
    "pickup full": [
        ("action", "drops $give and takes $item."),
        ("action", "hands $who $give in exchange for $item"),
        ("action", "is now carrying $item, but dropped $give."),
    ],
    "takes item": [
        ("action", "is now carrying $item."),
        ("action", "now contains $item."),
        ("reply", "Okay, $who."),
    ],
    "list items": [
        ("action", "contains $inventory."),
        ("reply", "I am carrying $inventory."),
        ("action", "is carrying $inventory."),
    ],
    "I want a present": [
        ("action", "gives $who $give"),
    ],
    "give someone a present": [
        ("action", "gives $someone $give"),
    ],
    # "uses reply":[],
    # "automatic haiku":[],
}

    
def init(dbname):
    '''
    Initialize the database
    '''

    db = sqlite3.connect(dbname)
    cur = db.cursor()

    cur.execute("PRAGMA foreign_keys = ON")
    
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

    # facts are association of three terms
    cur.execute("""
CREATE TABLE IF NOT EXISTS facts (
id INTEGER PRIMARY KEY AUTOINCREMENT,
subject_id INTEGER NOT NULL,
link_id INTEGER NOT NULL,
tidbit_id INTEGER NOT NULL,
FOREIGN KEY(subject_id) REFERENCES terms(id),
FOREIGN KEY(link_id) REFERENCES terms(id),
FOREIGN KEY(tidbit_id) REFERENCES terms(id),
UNIQUE(subject_id, link_id, tidbit_id)
)""")
    for fk in ("subject", "link", "tidbit"):
        cur.execute(f"""
CREATE INDEX IF NOT EXISTS {fk}_index ON facts({fk}_id)
        """)

    # Delete facts if any of their terms are deleted.
    cur.execute("""
CREATE TRIGGER purge_fact
BEFORE DELETE ON terms
BEGIN
    DELETE FROM facts WHERE subject_id = OLD.id;
    DELETE FROM facts WHERE link_id    = OLD.id;
    DELETE FROM facts WHERE tidbit_id  = OLD.id;
END
    """)

    # If we delete a factoid, delete the tidbit if no other facts
    # still reference it.
    cur.execute("""
CREATE TRIGGER prune_tidbit
AFTER DELETE ON facts
BEGIN
    DELETE FROM terms 
    WHERE terms.id = OLD.tidbit_id AND NOT EXISTS (
      SELECT 1 FROM facts WHERE tidbit_id = OLD.tidbit_id
    );
END
    """)

    #
    # Currently holding these items, item_id points to a value.
    #
    cur.execute("""
CREATE TABLE IF NOT EXISTS holding (
id INTEGER PRIMARY KEY AUTOINCREMENT,
item_id INTEGER NOT NULL,
FOREIGN KEY(item_id) REFERENCES terms(id),
UNIQUE(item_id)
)""")
    cur.execute("""
CREATE INDEX IF NOT EXISTS holding_index ON holding(item_id)
        """)
    cur.execute("""
CREATE TRIGGER drop_deleted_item
BEFORE DELETE ON terms
BEGIN
    DELETE FROM holding WHERE holding.item_id = OLD.id;
END
    """)

    db.commit()
    return db


if '__main__' == __name__:
    import sys
    import store
    try:
        dbfile = sys.argv[1]
    except IndexError:
        dbfile = ":memory:"
    bs = store.Bucket(dbfile)
    facts(bs)
    
