#!/usr/bin/env python3
'''
Prime a bucket with some entries
'''

import sqlite3

# System facts are used sort of like locale gettext.  The plugin code
# only knows about the subject keys and will resolve a tidibit to form
# a response.  In addition to system terms, known terms can contribute
# to the resolution.  Some system factoids have special terms
# provided, as indicated in comments.
system_facts = {

    # Meta factoids about factoids.  The special term: $thesubject,
    # the value of the current factoid under consideration.  Except
    # for factoid-unknown, two others, $thelinke and $thetidbit are
    # available.
    "factoid-unknown": [
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
        ("reply", "Sorry $who, I can't do that right now"),
        ("action", "dumps core"),
    ],
    "factoid-added": [
        ("reply", 'Okay, $who.'),
        ("reply", 'I am excited to learn about $thesubject!'),
        ("reply", 'Well now! Who knew that $thesubject $thelink $thetidbit?'),
    ],
    "factoid-duplicated": [
        ("reply", "$who, I already had it that way"),
        ("reply", "$who, I already that for $thesubject"),
        ("reply", "Yes, I know"),
        ("reply", "Don't teach grandma to suck eggs!"),
    ],

    # Non-item terms.  The special $thekind and $thetext are defined
    # and refer to the particular term kind and its text.

    "term-duplicated": [
        ("reply", '$who: I had it that way!'),
        ("reply", "But $thekind is already set with $thetext!"),
    ],
    "term-added": [
        ("reply", 'Okay $who'),
        ("action", "places $thetext on the growing $thekind mound"),
    ],
    "term-removed": [
        ("reply", 'Okay $who'),
        ("action", "kicks $thetext from the $thekind pool"),
    ],
    "term-unknown": [
        ("reply", '$who: never heard of it!'),
        ("action", "sees no $thekind $thetext"),
    ],
    "term-reserved": [
        ("reply", 'Sorry $who, "$thekind" terms are only for me!'),
        ("action", 'covets precious "$thekind" terms'),
    ],

    # items:

    # Give away an item.  The special $recipient is filled with the
    # name of who receives the gift.  The gift itself must be refered
    # to with $give which has a side effect to have the bot no longer
    # hold the item.
    "give-present": [
        ("action", "gives $recipient $give"),
        ("reply", "Hey, $recipient!  Here, for you: $give!"),
    ],

    # Item related handling. Where an item of interest exists $theitem
    # is defined.  
    "item-duplicated": [
        ("reply", '$who: I already have $theitem.'),
        ("reply", "But I've already got $theitem!"),
        ("reply", 'I already have $theitem.'),
        ("reply", "No thanks, $who, I've already got one."),
    ],
    # A $give must be used.
    "item-dropped": [
        ("action", "fumbles and drops $give."),
    ],
    # A $give must be used.
    "item-overflow": [
        ("action", "drops $give and takes $theitem."),
        ("action", "hands $who $give in exchange for $theitem"),
        ("action", "is now carrying $theitem, but dropped $give."),
    ],
    # No $theitem.
    "item-underflow": [
        ("reply", "Sorry, $who, I'm not carrying anything!"),
        ("action", "hunts under the cushions for some new stuff"),
    ],
    "item-taken": [
        ("action", "is now carrying $theitem."),
        ("action", "now contains $theitem."),
        ("reply", "Okay, $who."),
    ],
    # Special $inventory
    "item-list": [
        ("action", "contains $inventory."),
        ("reply", "I am carrying $inventory."),
        ("action", "is carrying $inventory."),
    ],

    # common conversations

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
CREATE TRIGGER IF NOT EXISTS purge_fact
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
CREATE TRIGGER IF NOT EXISTS prune_tidbit
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
CREATE TRIGGER IF NOT EXISTS drop_deleted_item
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
    
