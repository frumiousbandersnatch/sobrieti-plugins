#!/usr/bin/env python3
'''
Functions to publish stuff
'''

import requests

def post_0x0(fileobj, site="https://0x0.st"):
    '''
    Post dat to 0x0
    '''
    files = {"file": fileobj}
    got = requests.post(site, files=files)
    return got.text.strip()


post = post_0x0
    
