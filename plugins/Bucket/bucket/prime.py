#!/usr/bin/env python3
'''
Prime a bucket with some entries
'''

import sqlite3

system_facts = {
    "don't know": [
        "A thousand apologies, effendi, but I do not understand.",
        "Beeeeeeeeeeeeep!",
        "Can't talk, zombies!",
        "Error 42: Factoid not in database.  Please contact administrator of current universe.",
        "Error at 0x08: Reference not found",
        "I cannot access that data.",
        "I don't know",
        "I don't know anything about that.",
        "I'm sorry, there's currently nothing associated with that keyphrase.",
        "Not a bloody clue, sir.",
        "UNCAUGHT EXCEPTION: TERMINATING",
    ],
    "band name reply": [
        '"$band" would be a good name for a band.',
        '"$band" would be a nice name for a band.',
        '"$band" would be a nice name for a rock band.',
        '"$band" would make a good name for a band.',
        '"$band" would make a good name for a rock band.',
        'That would be a good name for a band.',
    ],
    "new fact": [
        'Okay, $who.',
        'I am excited to learn about $subject!',
    ],
    "existing fact": [
        "$who, I already had it that way",
        "Yes, I know",
    ],

    "duplicate item": [
        '$who: I already have $item.',
        "But I've already got $item!",
        'I already have $item.',
        "No thanks, $who, I've already got one.",
    ],
    "drops item": [
        "fumbles and drops $give.",
    ],
    "pickup full": [
        "drops $give and takes $item.",
        "hands $who $give in exchange for $item",
        "is now carrying $item, but dropped $give.",
    ],
    "takes item": [
        "is now carrying $item.",
        "now contains $item.",
        "Okay, $who.",
    ],
    "list items": [
        "contains $inventory.",
        "I am carrying $inventory.",
        "is carrying $inventory.",
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

    # facts
    cur.execute("""
CREATE TABLE IF NOT EXISTS facts (
id INTEGER PRIMARY KEY AUTOINCREMENT,
subject_id INTEGER NOT NULL,
link_id INTEGER NOT NULL,
tidbit_id INTEGER NOT NULL,
FOREIGN KEY(subject_id) REFERENCES terms(id) ON DELETE CASCADE,
FOREIGN KEY(link_id) REFERENCES terms(id)    ON DELETE CASCADE,
FOREIGN KEY(tidbit_id) REFERENCES terms(id)  ON DELETE CASCADE,
UNIQUE(subject_id, link_id, tidbit_id)
)""")

    for fk in ("subject", "link", "tidbit"):
        cur.execute(f"""
CREATE INDEX IF NOT EXISTS {fk}_index ON facts({fk}_id)
        """)

    # Currently holding these items, item_id points to a value.
    cur.execute("""
CREATE TABLE IF NOT EXISTS holding (
id INTEGER PRIMARY KEY AUTOINCREMENT,
item_id INTEGER NOT NULL,
FOREIGN KEY(item_id) REFERENCES terms(id) ON DELETE CASCADE,
UNIQUE(item_id)
)""")
    cur.execute("""
CREATE INDEX IF NOT EXISTS holding_index ON holding(item_id)
        """)
    
    cur.execute("""
CREATE TRIGGER drop_deleted_item
BEFORE DELETE ON terms
BEGIN
    DELETE FROM holding WHERE holding.item_id = OLD.id
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
    
