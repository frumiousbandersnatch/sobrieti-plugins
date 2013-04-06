#!/usr/bin/env python
'''
Upload/downoad QDB to pickle
'''

import pickle

#rashurl = 'http://stop.zzl.org/qdb'
rashurl = 'http://192.168.1.129/rqdb'
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

