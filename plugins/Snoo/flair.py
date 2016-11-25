#!/usr/bin/env python

import json
import requests

headers = {
    'Accept': 'application/json',
    'Content-Type': 'application/json; charset=UTF-8',
    'user-agent': 'sobrietibot'
}

comment_urlpat = "https://www.reddit.com/user/{username}/comments/{subreddit}.json"
search_urlpat = "https://www.reddit.com/r/{subreddit}/search.json"

def get_recent_search(subreddit, username):
    url = search_urlpat.format(**locals())
    params = dict(sort='new', q=username, restrict_sr='on', t='all')
    r = requests.get(url, params = params, headers=headers)
    return r.json()
def get_recent_comments(subreddit, username):
    url = comment_urlpat.format(**locals())
    params = dict(sort='new')
    r = requests.get(url, params = params, headers=headers)
    return r.json()
    
def get_data_entry(data, subreddit, username, entryname = 'author_flair_text'):
    if data is None: return
    data = data.get('data',None)
    if data is None: return
    children = data.get('children',[])
    for child in children:
        data = child.get('data',None)
        if data is None: continue
        sub = data.get('subreddit',None)
        if sub != subreddit: continue
        author = data.get('author',None)
        if author != username: continue
        return data.get(entryname, None)
    return

def get_flair(subreddit, username):
    res = get_recent_search(subreddit, username)
    if not res: 
        res = get_recent_comments(subreddit, username)
    if not res: 
        return
    flair = get_data_entry(res, subreddit, username)
    return flair


if __name__ == '__main__':
    import sys
    sub,user = sys.argv[1], sys.argv[2]
    flair = get_flair(sub, user) or 'no flair'
    print 'In %s, %s has flair: "%s"' % (sub, user, flair)


