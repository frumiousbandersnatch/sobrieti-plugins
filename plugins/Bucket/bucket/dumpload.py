#!/usr/bin/env python3
'''
Dump from XKCD Bucket MySQL and/or load to Pail sqlite3

>>> pip install mysql-connector-python
'''
import mysql.connector
from . import store


def fix_enc(text):
    'Try to fix encoding.'

    for encoding in ('latin-1', 'cp1252'):
        try:
            got = bytes(text, encoding, errors="ignore").decode()
            #print(f'{encoding}: {got}')
            return got.strip()
        except UnicodeDecodeError:
            continue
    got = bytes(text, 'cp1252', errors="ignore").decode(errors='ignore')    
    if not got.strip():
        return ""
    #print(f'give up: "{got}" from repr:"{repr(text)}" string:"{text}"')
    return got


def convert_items(mconn, bs):
    'Convert bucket_items into terms with kind="item".'
    #cur.execute("SELECT CONVERT(what USING latin1) FROM bucket_items WHERE id=39")
    mcur = mconn.cursor()
    #mcur.execute("SELECT id,CONVERT(what USING latin1),user FROM bucket_items")
    mcur.execute("SELECT id,what,user FROM bucket_items")
    count = 0;
    for one in mcur:
        #print(one)
        ident,text,user = one
        text2 = fix_enc(text)
        bs.term(text2, "item", False, creator=user)
        count += 1
    bs.db.commit()
    return count

def convert_vars(mconn, bs):
    'Convert bucket_vars/bucket_values into terms with kind according to .name'
    mcur = mconn.cursor()
    # mcur.execute("""SELECT
    # CONVERT(bucket_vars.name USING latin1) AS kind,
    # CONVERT(bucket_values.value USING latin1) as text
    # FROM bucket_vars
    # INNER JOIN bucket_values
    # ON bucket_values.var_id = bucket_vars.id""")
    mcur.execute("""SELECT
    bucket_vars.name AS kind,
    bucket_values.value as text
    FROM bucket_vars
    INNER JOIN bucket_values
    ON bucket_values.var_id = bucket_vars.id""")

    count = 0
    for kind,text in mcur:
        kind = fix_enc(kind)
        text = fix_enc(text)
        if not text.strip():
            continue
        bs.term(text, kind, False)
        count += 1
    bs.db.commit()
    return count

def convert_facts(mconn, bs):
    'Convert bucket_facts to term triplets'
    mcur = mconn.cursor()
    # mcur.execute("""SELECT
    # CONVERT(fact USING latin1) AS subject,
    # CONVERT(verb USING latin1) AS link,
    # CONVERT(tidbit USING latin1) AS tidbit
    # FROM bucket_facts""")
    mcur.execute("""SELECT fact, verb, tidbit
    FROM bucket_facts""")
    count = 0
    for subject,link,tidbit in mcur:
        if link.startswith("<") and link.endswith(">"):
            link = link[1:-1]

        if not subject.isascii():
            subject = fix_enc(subject)

        if not tidbit.isascii():
            tidbit = fix_enc(tidbit)
            if not tidbit.strip():
                continue

        bs.factoid(subject, link, tidbit, False)
        count += 1
    bs.db.commit()
    return count

def main(bs, host="localhost", user="bucket",
         password="bucket", database="bucket"):


    with mysql.connector.connect(host=host, user=user,
                                 password=password, database=database) as mconn:
        n = convert_items(mconn, bs)
        print(f'converted {n} items')
        n = convert_vars(mconn, bs)
        print(f'converted {n} vars')
        n = convert_facts(mconn, bs)
        print(f'converted {n} facts')

if '__main__' == __name__:
    import sys
    try:
        dbfile = sys.argv[1]
    except IndexError:
        dbfile = ":memory:"
    bs = store.Bucket(dbfile)
    main(bs)
    print(f'loaded to {dbfile}')

    
