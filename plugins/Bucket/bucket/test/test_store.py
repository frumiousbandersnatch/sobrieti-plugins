#!/usr/bin/env pytest
'''
❯ PYTHONPATH=.. pytest test/test_store.py
'''

import pytest
from bucket import store

def test_purge_items():
    'Purge item and assure no longer held'
    bs = store.Bucket()
    assert bs
    assert bs.sql("SELECT * FROM facts").fetchall()
    for one in "abc":
        bs.give_item(one)
    held = bs.held_items()
    print(held)
    assert len(held) == 3
    bs.purge_item("b")
    held = bs.held_items()
    print(held)
    assert len(held) == 2
    assert "b" not in held
    assert not bs.sql("SELECT * FROM terms WHERE text='b'").fetchall()
    
def _load_cats_and_dogs(bs):
    bs.factoid("cats", "are", "smart")
    bs.factoid("cats", "are", "stupid")
    bs.factoid("dogs", "are", "stupid")
    cats = bs.facts("cats")
    dogs = bs.facts("dogs")
    print("create", cats, dogs)
    assert len(cats) == 2
    assert len(dogs) == 1

def test_purge_factoid():
    'Remove factoid and assure terms are purged'
    bs = store.Bucket()
    _load_cats_and_dogs(bs)

    got = bs.sql("""
    SELECT subject_id,link_id,tidbit_id FROM facts fact
    INNER JOIN terms subject ON subject.id = fact.subject_id
    INNER JOIN terms link    ON link.id    = fact.link_id
    INNER JOIN terms tidbit  ON tidbit.id  = fact.tidbit_id
    WHERE subject.text=? AND link.text=? AND tidbit.text=?""",
           ("cats", "are", "stupid")).fetchall()
    for one in got:
        print("one:",one, type(one[0]))
        print(bs.sql("select * from terms where id = ?", (one[0],)).fetchone())
        print(bs.sql("select * from terms where id = ?", (one[1],)).fetchone())
        print(bs.sql("select * from terms where id = ?", (one[2],)).fetchone())

    bs.purge_factoid("cats", "are", "stupid")
    cats = bs.facts("cats")
    dogs = bs.facts("dogs")
    print("purge stupid cats", cats, dogs)
    assert len(cats) == 1
    assert len(dogs) == 1


    bs.purge_factoid("dogs", "are", "stupid")
    cats = bs.facts("cats")
    dogs = bs.facts("dogs")
    print("purge stupid dogs", cats, dogs)
    assert len(cats) == 1
    assert len(dogs) == 0

    # all stupidity gone
    assert not bs.sql("SELECT * FROM terms WHERE text = 'stupid'").fetchall()
    # one smart left
    assert bs.sql("SELECT * FROM terms WHERE text = 'smart'").fetchall()

    bs.purge_factoid("cats", "are", "smart")
    assert not bs.sql("SELECT * FROM terms WHERE text = 'smart'").fetchall()
    # smart term should be removed via trigger
    cats = bs.facts("cats")
    dogs = bs.facts("dogs")
    print("purge smart cats", cats, dogs)
    assert len(cats) == 0
    assert len(dogs) == 0

def test_purge_fact_subject():
    bs = store.Bucket()
    _load_cats_and_dogs(bs)
    bs.purge_subject("cats")
    cats = bs.facts("cats")
    dogs = bs.facts("dogs")
    print("purge cats", cats, dogs)
    assert len(cats) == 0
    assert len(dogs) == 1
    assert not bs.sql("SELECT * FROM terms WHERE text = 'smart'").fetchall()
    assert bs.sql("SELECT * FROM terms WHERE text = 'stupid'").fetchall()
    
