#!/usr/bin/env python
'''
Upload/downoad QDB to pickle
'''

import pickle
import json
import re
import cgi
from urllib import urlencode
from urllib2 import urlopen, HTTPError

rashurl = 'http://sobrieti.bot.nu/rqdb'
#rashurl = 'http://stop.zzl.org/qdb'
#rashurl = 'http://192.168.1.129/rqdb'
apiurl = rashurl + '/api.php'

def apicall(cmd, **params):
    args = dict(cmd=cmd)
    if params:
        args.update(params)

    url = apiurl + '?' + urlencode(args)
    print 'APICALL',url

    try: 
        fp = urlopen(url)
    except HTTPError, msg:
        print msg
        raise
    contents = fp.read()
    try:
        data = json.loads(contents)
    except ValueError,msg:
        print msg
        print contents
        return None
    return data


def format_quote_list(data):
    ids = ', '.join(['[%s]'%d['id'] for d in data])
    return 'quotes: %s' % ids

def format_quote(data, maxlen = None):
    '''
    Format the data returned from an API get into a single line.

    Punt if it is longer than maxlen.
    '''
    q = data['quote']
    q = q.replace('&lt;','<').replace('&gt;','>').replace('\r\n',' | ')
    q = q.replace('&quot;','"')
    q = ' '.join(q.split())
    n = data['id']
    s = data['rating']
    u = '%s/?%s' % (rashurl, n)
    maybe = '#%s(%s): [%s] %s' % (n,s,u,q)
    if maxlen is None or len(maybe) < maxlen:
        return maybe
    return '#%s(%s): [ %s ] (long quote, see web page)' % (n,s,u)
        
# http://stackoverflow.com/questions/275174/how-do-i-perform-html-decoding-encoding-using-python-django
# http://stackoverflow.com/questions/1061697/whats-the-easiest-way-to-escape-html-in-python
def wash_quote(line, newline='|'):
    '''
    Return \n-separted string suitable for adding to qdb.

    It tries to find breaks based on "|" characters and "<nick>" markup.
    '''
    out = []
    for word in line.split():
        word = word.strip()

        if word == newline:
            out.append('\n')
            continue

        if re.search(r'<\w+>', word):
            out.append('\n')
        out.append(word)
        continue
    return cgi.escape(' '.join(out))


def upload_file(filename):
    '''
    Load a text file with one quote per line
    '''
    fp = open(filename)
    for line in fp.readlines():
        quote = wash_quote(line.strip()).strip()
        data = apicall('add', quote=quote)
        print data
        continue
    return

if '__main__' == __name__:
    import sys
    ### use carefuly!
    #upload_file(sys.argv[1])

    
    
    
