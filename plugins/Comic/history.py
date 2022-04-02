#!/usr/bin/env python

from collections import defaultdict, namedtuple
from datetime import datetime

Context = namedtuple("Context", "network channel")
Event = namedtuple("Event", "time nick text")

class DB:
    '''
    Retain recent chat history on a per-channel basis.
    '''
    def __init__(self, term_s = 120):
        '''
        Create per channel history which remembers no more than term_s
        seconds.  This store is ephemeral in memory.
        '''
        self._term = term_s
        self._store = defaultdict(list)
    
    def context(self, channel="", network=""):
        'Return context object.'
        return Context(network, channel)

    def event(self, nick, text):
        'Return an event object'
        now = datetime.now()
        return Event(now, nick, text)

    def remember(self, nick, text, channel="", network=""):
        '''
        Add event to history.
        '''
        ctx = self.context(channel, network)
        evt = self.event(nick, text)
        self._store[ctx].append(evt)
        self.normalize(ctx)

    def recall(self, channel="", network=""):
        '''
        Recall list of events.  May be empty.
        '''
        ctx = self.context(channel, network)
        self.normalize(ctx)
        return self._store[ctx]

    def normalize(self, ctx):
        '''
        Prune any history for context
        '''
        evts = self._store[ctx]
        if not evts:
            return
        last = evts[-1].time
        while evts:
            delta = last - evts[0].time
            if delta.seconds <= self._term:
                break
            evts.pop(0)

