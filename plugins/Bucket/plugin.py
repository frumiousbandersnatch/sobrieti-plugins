###
# Copyright (c) 2021, Frumious Bandersnatch
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import sys
def chirp(*msgs):
    sys.stderr.write(' '.join([repr(m) for m in msgs]) + '\n')

import re
from importlib import reload
from . import bucket
reload(bucket)

import supybot.ircmsgs as ircmsgs
from supybot import utils, plugins, ircutils, callbacks
from supybot.commands import *
try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('Bucket')
except ImportError:
    # Placeholder that allows to run the plugin on a bot
    # without the i18n module
    _ = lambda x: x


# msg.nick is sender nick
# msg.args[0] is channel
# msg.args[1] is message
# - if privmsg then simple text
# - if action then \x01ACTION the action\x01
# irc.nick is bot nick

class Bucket(callbacks.PluginRegexp, plugins.ChannelDBHandler):
    """Mostly compatible implementation of XKCD Bucket"""
    threaded = True
    public = True
    regexps = []
    addressedRegexps = ["factoid", "explain", "matchlike", "junk_addr"]
    unaddressedRegexps = ["say", "items1", "items2", "junk_unaddr"]

    def invalidCommand(self, irc, msg, tokens):
        s = ' '.join(tokens)
        for (r, name) in self.addressedRes:
            self.log.debug(f'Bucket: dispatch {name} {repr(r)} {repr(s)}')
            for m in r.finditer(s):
                self._callRegexp(name, irc, msg, m)

    def __init__(self, irc):
        callbacks.PluginRegexp.__init__(self, irc)
        plugins.ChannelDBHandler.__init__(self)

    def makeDb(self, filename):
        chirp(f"MAKEDB: {filename}")
        return bucket.store.Bucket(filename)

    def say(self, irc, msg, regex):
        r"^say (?P<sentence>.*$)"
        text = regex["sentence"]
        # fixme: strip off non-word chars from text
        text = text.capitalize() + "!"
        chirp(f'say: msg:|{repr(msg.args[1])}|, regex:|{repr(regex)}| -> |{text}|')
        self.log.debug(f'say: msg:|{msg}|, regex:|{regex}| -> |{text}|')
        irc.reply(text, prefixNick=False)

    def inventory(self, irc, msg, args, channel):
        """[<channel>]

        What is in the bucket?
        """
        db = self.getDb(channel)
        have = db.held_items()
        if not have:
            more = dict(who=msg.nick, to=irc.nick)
            reply = db.choose_factoid("empty bucket")            
            chirp(f"INVENTORY: {reply}")
            self._factoid_response(irc, msg, reply)
            return
            
        have = ', '.join(have)
        reply = f'is carrying {have}.'
        chirp(f"INVENTORY: {reply}")
        irc.reply(reply, prefixNick=False, action=True)
    inventory = wrap(inventory, ['channeldb'])

    def literal(self, irc, msg, args, channel, subject):
        """[<channel>] <subject>

        All that is known about a subject.
        """
        chirp(f"LITERAL: {subject}")
        db = self.getDb(channel)
        lines = []
        for fid, (s,l,t) in sorted(db.factoids(subject).items()):
            if l not in ("is","are"):
                l = f'<{l}>'
            lines.append(f'(#{fid}) {l} {t}')
        body = '|'.join(lines)
        reply = f'{subject} {body}'
        chirp(f"LITERAL: {reply}")
        irc.reply(reply)
    literal = wrap(literal, ['channeldb', 'text'])

    def give(self, irc, msg, args, channel, item):
        """[<channel>] <item>

        Gimme something!
        """
        self._itemsx(irc, msg, dict(nick=irc.nick, item=item))
    give = wrap(give, ['channeldb', 'text'])

    ### Common for items1/items2 because I do not know how to combine
    ### all three regexp into one....
    def _itemsx(self, irc, msg, regex):
        chan = msg.args[0]
        me = regex["nick"]
        item = regex["item"]

        if me != irc.nick:
            return
        db = self.getDb(chan)

        # add "someone", etc.  and move this to a single method
        more = dict(who=msg.nick, to=irc.nick, item=item)

        have = db.held_items()
        if item in have:
            _,_,reply = db.choose_factoid("duplicate item")            
            reply = db.resolve(reply, **more)
            chirp(f"ITEMSX: have: {reply}")
            irc.reply(reply, prefixNick=False, action=False)
            return

        max_items = self.registryValue('max_items')
        if len(have) >= max_items:
            _,_,reply = db.choose_factoid("pickup full")
        else:
            _,_,reply = db.choose_factoid("takes item")

        reply = db.resolve(reply, **more)

        # must give item after resolution as a 'pickup full' will drop
        # one and we don't want to drop the one we were just given.
        db.give_item(item)

        chirp(f"ITEMSX: {reply}")
        irc.reply(reply, prefixNick=False, action=False)
        return

    # /me puts {item} in Bucket.
    # /me gives {item} to Bucket
    def items1(self, irc, msg, regex):
        r"^\x01ACTION (?:gives|puts) (?P<item>.+?) (?:to|in) (?P<nick>[^ ]+?)\x01$"
        self._itemsx(irc, msg, regex)

    # /me gives Bucket {item}
    def items2(self, irc, msg, regex):
        r"^\x01ACTION gives (?P<nick>[^ ]+) (?P<item>.+?)\x01$"
        self._itemsx(irc, msg, regex)

    def junk_addr(self, irc, msg, regex):
        r".*"
        chirp(f'ADDRESSED: msg:|{repr(msg.args[1])}|, regex:|{repr(regex)}|')
        self.log.debug(f'addressed: msg:|{repr(msg.args[1])}|, regex:|{repr(regex)}|')
    def junk_unaddr(self, irc, msg, regex):
        r"^(?!say).*"
        chirp(f'UNADDRESSED: msg:|{repr(msg.args[1])}|, regex:|{repr(regex)}|')
        self.log.debug(f'unaddressed: msg:|{msg}|, regex:|{regex}|')

    def factoid(self, irc, msg, regex):
        r"^(?P<subject>.*) +(?P<link>is|are|[<][^>]+[>]) +(?P<tidbit>.*)$"
        chan = msg.args[0]
        if not regex:
            self.log.debug(f'factoid: no match {repr(msg.args[1])}')
            return

        subject = regex['subject']
        tidbit = regex['tidbit']
        link = regex['link']
        if link.startswith("<") and link.endswith(">"):
            link = link[1:-1]
        if not all ((subject, link, tidbit)):
            self.log.debug(f'factoid: incomplete "{subject}" "{link}" "{tidbit}"')
            return
        
        more = dict(who=msg.nick, to=irc.nick, subject=subject)

        db = self.getDb(chan)
        fid, new = db.factoid(subject, link, tidbit)
        if new:
            rep_sub = "new fact"
        else:
            rep_sub = "existing fact"
        _,_,reply = db.choose_factoid(rep_sub)
        self.log.debug(f'factoid: |{subject}|{link}|{tidbit}| -> |{reply}|')
        reply = db.resolve(reply, **more)
        chirp(f'factoid: |{subject}|{link}|{tidbit}| -> |{reply}|')
        irc.reply(reply, prefixNick=False, action=False)        

    def _factoid_response(self, irc, msg, factoid, **more):
        '''
        Respond with a factoid
        '''
        chan = msg.args[0]
        db = self.getDb(chan)

        # fixme: $someone, etc
        more.update(who=msg.nick, to=irc.nick)
        subject, link, tidbit = factoid
        tidbit = db.resolve(tidbit, **more)            
        if link == 'reply':
            chirp(f'REPLY: |{tidbit}|')
            irc.reply(tidbit, prefixNick=False)
            return
        if link == 'action':
            chirp(f'ACTION: |{tidbit}|')
            irc.reply(tidbit, action=True)
            return
        reply = ' '.join([subject, link, tidbit])
        chirp(f'RESPONSE: |{reply}|')
        irc.reply(reply)

    def _dont_know(self, irc, msg, **more):
        '''
        Shruggy shoulder
        '''
        chan = msg.args[0]
        db = self.getDb(chan)
        _,_,reply = db.choose_factoid("don't know")
        chirp(f'DO NOT KNOW: |{reply}|')
        irc.reply(reply)

    def explain(self, irc, msg, regex):
        r"^(?P<subject>((?!\s*is|are|[<][^>]+[>]).)*)$"
        chirp(f'EXPLAIN: msg:|{repr(msg.args[1])}|, regex:|{repr(regex)}|')
        self.log.debug(f'explain: msg:|{msg}|, regex:|{regex}|')
        chan = msg.args[0]
        db = self.getDb(chan)
        subject = regex['subject']
        try:
            _,link,tidbit = db.choose_factoid(subject)
        except KeyError:
            self._dont_know(irc, msg)
            return
        self._factoid_response(irc, msg, (subject, link, tidbit))

    def matchlike(self, irc, msg, regex):
        r"^(?P<subject>(?!\s*=!.)*) =~ (?P<match>.*)$"
        chan = msg.args[0]
        db = self.getDb(chan)
        subject = regex['subject']
        parts = regex['match'].split("/")
        
        if len(parts) == 1:
            _,link,tidbit = db.choose_factoid_like(subject, parts[0])
            self._factoid_response(irc, msg, (subject, link, tidbit))
            return
        # for now, no support for edit
            
            

Class = Bucket


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
