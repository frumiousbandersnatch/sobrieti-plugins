#!/usr/bin/env python3
'''
Prime a bucket with some entries
'''

default_special_replies = {
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
def facts(bs, data=default_special_replies, link='reply'):
    '''
    Fill special replies
    '''
    for subject, tidbits in data.items():
        for tidbit in tidbits:
            bs.factoid(subject, link, tidbit, False)
    bs.db.commit()
    
if '__main__' == __name__:
    import sys
    import store
    try:
        dbfile = sys.argv[1]
    except IndexError:
        dbfile = ":memory:"
    bs = store.Bucket(dbfile)
    facts(bs)
    
