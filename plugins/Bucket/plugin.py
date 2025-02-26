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

import re
import time
import random
from collections import defaultdict
from importlib import reload
from . import bucket
reload(bucket)

import supybot.ircdb as ircdb
import supybot.ircmsgs as ircmsgs
from supybot import utils, plugins, ircutils, callbacks
from supybot.commands import *
import supybot.world as world
import supybot.schedule as schedule

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

# histories:
# triggered factoids
# seen nicks
# seen opers
# per nick lines

class TransientChannelHistory:
    'Track recent things in a channel'
    def __init__(self, maxsaid=100, maxfact=100):
        self._maxsaid = maxsaid
        self._maxfact = maxfact
        self.nicks = list()
        self.said = defaultdict(list)
        self.triggered = list()

    def add_msg(self, msg):
        try:
            self.nicks.remove(msg.nick)
        except ValueError:
            pass
        self.nicks.insert(0, msg.nick)

        said = self.said[msg.nick]
        pmsg = ircmsgs.prettyPrint(msg)
        self.said[msg.nick] = [pmsg] + said[:self._maxsaid-1]
        
    def add_factoid(self, factoid):
        self.remove_factoid(factoid)
        self.triggered = [factoid] + self.triggered[:self._maxfact-1]
    def remove_factoid(self, factoid):
        try:
            self.triggered.remove(factoid)
        except ValueError:
            pass
        

class TransientHistory:
    'Track recent things'
    def __init__(self, maxlen=100):
        self.hist = defaultdict(TransientChannelHistory)

    def add_msg(self, msg):
        if not msg.channel:
            return
        self.hist[msg.channel].add_msg(msg)
    def add_factoid(self, channel, factoid):
        if not channel:
            return
        self.hist[channel].add_factoid(factoid)
    def remove_factoid(self, channel, factoid):
        if not channel:
            return
        self.hist[channel].remove_factoid(factoid)
    def get_factoids(self, channel):
        if not channel:
            return []
        return self.hist[channel].triggered

    def not_you(self, msg):
        if not msg.channel:
            return []
        nicks = list(self.hist[msg.channel].nicks)
        try:
            nicks.remove(msg.nick)
        except ValueError:
            return []
        return nicks

    def anyone(self, msg):
        nicks = self.not_you(msg)
        try:
            return random.choice(nicks)
        except IndexError:
            return ""

    def someone(self, msg):
        nicks = self.not_you(msg)        
        try:
            return nicks[0]
        except IndexError:
            return ""

    def opnick(self, msg):
        return ""

    def more(self, msg):
        return dict(who=msg.nick,
                    anyone=self.anyone(msg),
                    someone=self.someone(msg),
                    op=self.opnick(msg))


class Bucket(callbacks.PluginRegexp, plugins.ChannelDBHandler):
    """Mostly compatible implementation of XKCD Bucket"""
    threaded = False
    public = True
    regexps = []
    addressedRegexps = ["a_re_goaway", "a_re_comeback",
                        "a_re_factoid", "a_re_explain", "a_re_matchlike",
                        #"junk_addr"
                        ]
    unaddressedRegexps = ["un_re_say", "un_re_items1", "un_re_items2",
                          #"junk_unaddr"
                          ]

    def __init__(self, irc):
        callbacks.PluginRegexp.__init__(self, irc)
        plugins.ChannelDBHandler.__init__(self)
        self.hist = TransientHistory()
        self.meek = defaultdict(bool)       # do not respond to unaddressed when true.

    def makeDb(self, filename):
        return bucket.store.Bucket(filename)

    def invalidCommand(self, irc, msg, tokens):
        self.log.debug(f'Bucket({irc.nick}): invalidCommand(msg:|[{repr(msg.args[0])}, {repr(msg.args[1])}]|, tokens:|{repr(tokens)}|)')

        if msg.args[1].startswith(irc.nick + ' '):
            self.log.debug(f'Bucket({irc.nick}): not replying to space-nick')
            irc.noReply()
            return

        # fixme: call this block via super(), for now we chirp inside
        s = ' '.join(tokens)
        for (r, name) in self.addressedRes:
            self.log.debug(f'Bucket: dispatch addressed meth:|{name}| regex:|{repr(r)}| string:|{repr(s)}|')
            for m in r.finditer(s):
                self._callRegexp(name, irc, msg, m)
                if 'ignored' in msg.tags or 'repliedTo' in msg.tags:
                    self.log.debug(f'Bucket: regex satisfied {msg.tags}')
                    return
        self.log.debug(f'Bucket: regex not satisfied')

        self.log.debug(f'Bucket: invalidCommand: tags: {msg.tags}')
        if 'ignored' in msg.tags or 'repliedTo' in msg.tags:
            return
        self._reply(irc, msg, 'factoid-unknown', thesubject=msg.addressed)

    def doPrivmsg(self, irc, msg):
        self.hist.add_msg(msg)

        if self.meek[msg.channel]:
            self.log.debug(f'MEEK: ignoring unaddressed: "{msg.args}"')
            irc.noReply()
            return

        # unaddressed
        callbacks.PluginRegexp.doPrivmsg(self, irc, msg)
        if 'ignored' in msg.tags or 'repliedTo' in msg.tags:
            self.log.debug(f'privmsg handled by regex: {msg.tags}')
            return

        # fixme: use configured 
        # supybot.reply.whenAddressedBy.chars
        if msg.args[1].startswith('@'):
            return

        line = msg.args[1]
        self.log.debug(f'UNMATCHED1: str:|{line}| repr:|{repr(line)}|, tags: {msg.tags}')
        got = re.compile('\x01ACTION (?P<line>.*?)\x01').match(line)
        if got:
            line = got['line']
            self.log.debug(f'UNMATCHED2: str:|{line}| repr:|{repr(line)}|')

        # OG bucket seems to not freely reply to "hi" but will to others.
        min_to_reply = self.registryValue('min_to_reply')
        if len(msg.args[1]) < min_to_reply:
            return

        if line.startswith(irc.nick):
            return
        
        self._reply(irc, msg, line, addressed=False)
        

    def un_re_say(self, irc, msg, regex):
        r"^say (?P<sentence>.*$)"
        text = regex["sentence"]
        # fixme: strip off non-word chars from text
        text = text.capitalize() + "!"
        self.log.debug(f'say: msg:|{msg}|, regex:|{regex}| -> |{text}|')
        irc.reply(text, prefixNick=False)


    @wrap(['channeldb'])
    def inventory(self, irc, msg, args, channel):
        """[<channel>]

        What items do the bucket hold?
        """
        db = self.getDb(channel)
        have = db.held_items(return_ids=True)
        if not have:
            self._reply(irc, msg, "item-underflow")
            return
        lines = []
        for one,iid in have:
            lines.append(f'{iid}: {one}')
        body = ' |'.join(lines)
        self._reply(irc, msg, "item-list", inventory=body)

    @wrap(['channeldb', 'text'])
    def literal(self, irc, msg, args, channel, subject):
        """[<channel>] <subject>

        All that is known about a factoid subject.
        """
        db = self.getDb(channel)
        lines = []
        for fid, (s,l,t) in sorted(db.factoids(subject).items()):
            if l not in ("is","are"):
                l = f'<{l}>'
            lines.append(f'{fid}: {l} {t}')
        if not lines:
            self._reply(irc, msg, 'factoid-empty', thesubject=subject)
            return

        self.log.debug(f'literal: "{subject}": {lines}')
        body = ' |'.join(lines)
        reply = f'{subject}: |{body}'
        irc.reply(reply)
        # fixme: use system-subject

    @wrap(['channeldb', 'something', 'text'])        
    def add(self, irc, msg, args, channel, kind, text):
        """[<channel>] <kind> <text>

        Tell me some kind of text.
        """
        db = self.getDb(channel)
        creator = self._getUsername(msg)
        if kind in db.system_kinds():
            creator = db.system_nick
            cap_needed = 'system'
            if not self._isCapable(msg, cap_needed):
                self._reply(irc, msg, "term-locked",
                            thekind=kind, thecapability=cap_needed)
                return

        have = db.terms(kind)
        if text in have:
            rep_sub = "term-duplicated"
        else:
            rep_sub = "term-added"
            db.term(text, kind, creator=creator)
        self._reply(irc, msg, rep_sub, thekind=kind, thetext=text)

    def _remove_term(self, irc, msg, db, ident):
        kt = db.idterm(ident)
        if not kt:
            self._reply(irc, msg, 'term-unknown', thekind='', thetext='')
            return
        kind, text = kt

        if kind in db.system_kinds():
            cap_needed = 'system'
            if not self._isCapable(msg, cap_needed):
                self._reply(irc, msg, "term-locked",
                            thekind=kind, thecapability=cap_needed)
                return

        db.purge_term(text, kind)
        self._reply(irc, msg, "term-removed", thekind=kind, thetext=text)

    def _remove_factoid(self, irc, msg, db, ident):
        factoid = db.idfactoid(ident)
        if not factoid:
            self._reply(irc, msg, 'factoid-unknown')
            return

        recent_n = self.registryValue('recent_volatile')

        # fixme: maybe let people remove w/out caps if they are creator
        lf = db.recent_factoids(recent_n, return_facts=False)
        if ident not in lf: # old ones need permission to purge
            if db.is_system_fact(factoid):
                cap_needed = 'system'
            else:
                cap_needed = 'op'
            if not self._isCapable(msg, cap_needed):
                self._reply(irc, msg, "factoid-locked",
                            thecapability=cap_needed, thesubject=factoid[0])
                return

        s,l,t = factoid
        db.purge_factoid(s,l,t)
        self.hist.remove_factoid(msg.channel, factoid)
        self._reply(irc, msg, "factoid-removed",
                    thesubject=s, thelink=l, thetidbit=t)

    @wrap(['channeldb', ('literal', ('term', 'factoid')), 'int'])
    def remove(self, irc, msg, args, channel, which, ident):
        """[<channel>] (term|factoid) <ID>

        I can forget a term or a factoid but I need its ID number.
        """
        db = self.getDb(channel)
        if which == "term":
            self._remove_term(irc, msg, db, ident)
        else:
            self._remove_factoid(irc, msg, db, ident)
        
    @wrap(['channeldb', 'text'])
    def forget(self, irc, msg, args, channel, what):
        """[<channel>] <what>

        Forget a factoid.  When <what> is "that" or "last", forget the
        most recently triggered.  If <what> is a number, then forget
        the n'th triggered ("that" is same as 0).
        """
        db = self.getDb(channel)
        lts = self.hist.get_factoids(msg.channel)
        fids = [db.factoidid(one) for one in lts]
        self._remove_factoid_from_ids(irc, msg, db, what, fids)

    @wrap(['channeldb', 'text'])
    def undo(self, irc, msg, args, channel, what):
        """[<channel>] <what>

        Undo a recently made factoid.  When <what> is "that" or "last"
        undo the most recently defined factoid.  If <what> is a number
        then forget the n'th oldest ("last" is same as 0).
        """
        db = self.getDb(channel)
        recent_n = self.registryValue('recent_volatile')
        fids = db.recent_factoids(recent_n, return_facts=False)
        self._remove_factoid_from_ids(irc, msg, db, what, fids)

    def _remove_factoid_from_ids(self, irc, msg, db, what, fids):
        'Handle choosing and checking if in channel'

        if not fids:
            irc.reply("No recent factoids")
            return

        if not msg.channel:
            irc.reply("I can only do this in a channel")
            return

        if what in ("that", "last"):
            index = 0
        else:
            try:
                index = int(what)
            except ValueError:
                irc.reply("Uh, no") # fixme, use _reply
                return

        try:
            fid = fids[index]
        except IndexError:
            irc.reply("I don't remember that many")
            return

        self._remove_factoid(irc, msg, db, fid)
        return fid



    @wrap(['channeldb', ('literal', ('recent', 'show', 'undo')), optional('int')])
    def factoids(self, irc, msg, args, channel, cmd, ident):
        """[<channel>] (recent|show|undo) [<ID>]

        Do things with factoids.  Some need 'op' capability.
        """
        self.log.debug(f'FACTOIDS: cmd:|{repr(cmd)}| ident:|{repr(ident)}|')

        db = self.getDb(channel)
        if cmd == "show":
            slt = db.idfactoid(int(ident))
            if not slt:
                self._reply(irc, msg, 'factoid-unknown', thesubject="that fact")
                return
            self._reply(irc, msg, slt)
            return

        recent_n = self.registryValue('recent_volatile')
        if cmd == "recent":
            lf = db.recent_factoids(recent_n)
            if not lf:
                irc.reply("no recent factoids")
                return
            lines = []
            for fid, slt in lf:
                f = ' '.join(slt)
                lines.append((f'{fid}: {f}'))
            body = ' |'.join(lines)
            irc.reply(f'recent factoid IDs: |{body}')
            return

        if cmd == "undo":
            self._undo(ir, msg, db, 0)

    @wrap(['channeldb', 'text'])
    def terms(self, irc, msg, args, channel, kind):
        """[<channel>] <kind>

        I can tell you all terms of a kind that I know.
        """
        db = self.getDb(channel)
        have = db.terms(kind, return_ids=True)
        if not have:
            self._reply(irc, msg, 'term-unknown', thekind=kind)
            return
        lines = []
        for one,tid in have:
            lines.append(f'{tid}: {one}')
        body = ' |'.join(lines)
        self._reply(irc, msg, "term-list", thekind=kind, inventory=body)
        # fixme: use system-subject

    @wrap(['channeldb'])
    def kinds(self, irc, msg, args, channel):
        """[<channel>] 

        You can see what kinds of variables I know.
        """
        db = self.getDb(channel)
        system = db.system_kinds()
        kinds = list(db.known_kinds().difference(system))

        kinds.sort()
        kinds = '", "'.join(kinds)

        system = list(system)
        system.sort()
        system = '", "'.join(system)

        irc.reply(f'System kinds: "{system}"')
        irc.reply(f'User kinds: "{kinds}"')
        # fixme: use system-subject

    @wrap(['channeldb', 'text'])
    def drop(self, irc, msg, args, channel, ioid):
        """[<channel>] <item_or_ID>

        Sometimes I hold things I shouldn't, but I can let them go.
        """
        db = self.getDb(channel)
        for text, iid in db.held_items(return_ids=True):
            if text == ioid or str(iid) == ioid:
                db.drop_item(text)
                self._reply(irc, msg, 'item-dropped', theitem=text)
                return
        self._reply(irc, msg, 'item-unknown')

    @wrap(['channeldb', 'text'])
    def give(self, irc, msg, args, channel, text):
        """[<channel>] <text>

        Gimme something, give you something, give them something!
        """
        db = self.getDb(channel)

        got = re.compile(r"(?P<name>^[^ ]+) a present").match(text)
        if not got:
            got = re.compile(r"a present to (?P<name>^[^ ]+)").match(text)
        if got:
            name = got['name']  # default literal name
            if name == "me":
                name = msg.nick
            if name == "someone":
                name = self.hist.someone(msg)
            if name == "anyone":
                name = self.hist.anyone(msg)
            if name in ("ops","chanop"):
                name = self.hist.opnick(msg)
            if len(db.held_items()) == 0:
                self._reply(irc, msg, 'item-underflow')
                return

            self._reply(irc, msg, 'give-present', recipient=name)
            return
            
        # otherwise, they are giving MEEEE something!
        fakeregex = dict(nick=irc.nick, item=text)
        self._itemsx(irc, msg, fakeregex)

    ### Common for items1/items2 because I do not know how to combine
    ### all three regexp into one....
    def _itemsx(self, irc, msg, regex):

        me = regex["nick"]
        if me != irc.nick:
            self.log.debug(f'itemsx: {me} is not {irc.nick}')
            return

        item = regex["item"]

        chan = msg.args[0]
        db = self.getDb(chan)

        have = db.held_items()
        if item in have:
            self._reply(irc, msg, "item-duplicated",
                        addressed=False, theitem=item)
            return

        max_items = self.registryValue('max_items')
        if len(have) >= max_items:
            rep_sub = "item-overflow"
        else:
            rep_sub = "item-taken"
        self._reply(irc, msg, rep_sub,
                    addressed=False, theitem=item)

        # We must give item after reply resolution as an
        # 'item-overflow' factoid is expected to have a $give and we
        # don't want to give away the item we were just given.
        db.give_item(item)
        return

    # /me puts {item} in Bucket.
    # /me gives {item} to Bucket
    def un_re_items1(self, irc, msg, regex):
        r"^\x01ACTION (?:gives|puts) (?P<item>.+?) (?:to|in) (?P<nick>[^ ]+?)\x01$"
        self.log.debug(f'say: msg:|{msg}|, regex:|{regex}|')
        self.log.debug(f"items1: {regex.groups()}")
        self._itemsx(irc, msg, regex)

    # /me gives Bucket {item}
    def un_re_items2(self, irc, msg, regex):
        r"^\x01ACTION gives (?P<nick>[^ ]+) (?P<item>.+?)\x01$"
        self.log.debug(f"items2: {regex.groups()}")
        self._itemsx(irc, msg, regex)

    # fixme, seek optional "bot, " or "bot: " prefix so when I forget
    # and explicitly address the bot in PM it will do the right thing.
    def a_re_factoid(self, irc, msg, regex):
        r"^(?P<subject>.*?)\s+(?P<link>is|<[^>]+>|are)\s+(?P<tidbit>.*)$"
        # r"^(?P<subject>.*) +(?P<link>[<][^>]+[>]|is|are) +(?P<tidbit>.*)$"
        self.log.debug(f'factoid: msg:|{msg}|, regex:|{regex}|')
        self.log.debug(f'factoid: regex dict: {regex.groupdict()}')
        chan = msg.args[0]
        db = self.getDb(chan)

        subject = regex['subject']
        creator = self._getUsername(msg)
        if db.is_system_fact(subject):
            self.log.debug(f'factoid: is system: "{subject}"')
            creator = db.system_nick
            cap_needed = 'system'
            if not self._isCapable(msg, cap_needed):
                self._reply(irc, msg, "factoid-locked",
                            thesubject=subject, thecapability=cap_needed)
                return

        tidbit = regex['tidbit']
        link = regex['link']
        if link.startswith("<") and link.endswith(">"):
            link = link[1:-1]
        if not all ((subject, link, tidbit)):
            self._reply(irc, msg, "factoid-broken")
            return


        fid, new = db.factoid(subject, link, tidbit, creator=creator)
        if new:
            rep_sub = "factoid-added"
        else:
            rep_sub = "factoid-duplicated"
        self._reply(irc, msg, rep_sub, thesubject=subject, thelink=link, thetidbit=tidbit)
        return

    def a_re_explain(self, irc, msg, regex):
        r"^(?P<subject>((?!\s*is|are|[<][^>]+[>]).)*)$"
        self.log.debug(f'explain: msg:|{msg}|, regex:|{regex}|')
        chan = msg.args[0]
        db = self.getDb(chan)
        subject = regex['subject']
        try:
            reply = db.choose_factoid(subject)
        except KeyError:
            reply = db.choose_factoid("factoid-unknown")
        self._reply(irc, msg, reply, thesubject=subject)

    def a_re_matchlike(self, irc, msg, regex):
        r"^(?P<subject>(?!\s*=!.)*) =~ (?P<match>.*)$"
        self.log.debug(f'matchlike: msg:|{msg}|, regex:|{regex}|')

        chan = msg.args[0]
        db = self.getDb(chan)
        subject = regex['subject']
        parts = regex['match'].split("/")
        
        if len(parts) == 1:
            reply = db.choose_factoid_like(subject, parts[0])
            self._reply(irc, msg, reply)
            return
        # for now, no support for edit
            
    def _set_come_back_event(self, channel, delay):
        'Set a come back event for channel for delay seconds in the future and go meek'
        event = self._del_come_back_event(channel)
        self.log.debug(f'MEEK: set event "{event}"')
        self.meek[channel] = True
        later = time.time() + delay
        def restore():
            self.log.debug("MEEK: I'm back, biatch!")
            self.meek[channel] = False
        schedule.addEvent(restore, later, name=event)

    def _del_come_back_event(self, channel):
        'remove come back event for channel if there and stop being meek'
        event = channel+'_come_back'
        self.log.debug(f'MEEK: del event "{event}"')
        try:
            schedule.removeEvent(event)
        except KeyError:
            pass
        self.meek[channel] = False
        return event

    def a_re_goaway(self, irc, msg, regex):
        r"^(?P<what>go away|fuck off|shut up)$"
        # people can be so cruel
        self.log.debug(f'goaway: msg:|{msg}|, regex:|{regex}|')

        if not msg.channel:
            irc.reply("Yell at me in a channel, not in a PM")
            return
        delay = self.registryValue('meek_time')
        self._reply(irc, msg, 'go-away', thechannel=msg.channel, theduration=delay)
        self._set_come_back_event(msg.channel, delay)
        
    def a_re_comeback(self, irc, msg, regex):
        r"^(?P<what>come back)$"
        self.log.debug(f'comeback: msg:|{msg}|, regex:|{regex}|')
        if not msg.channel:
            irc.reply("No channel to come back to")
            return
        self._del_come_back_event(msg.channel)
        self._reply(irc, msg, 'come-back', thechannel=msg.channel)

    def junk_addr(self, irc, msg, regex):
        r".*"
        self.log.info(f'addressed: msg:|{repr(msg.args[1])}|, regex:|{repr(regex)}|')

    def junk_unaddr(self, irc, msg, regex):
        r"^(?!say).*"
        self.log.info(f'unaddressed: msg:|{repr(msg.args[1])}|, regex:|{repr(regex)}|')
        m1 = re.compile(self.un_re_items1.__doc__).match(msg.args[1])
        if m1:
            self.log.info(f"M1: {m1.groups()}")
        m2 = re.compile(self.un_re_items2.__doc__).match(msg.args[1])
        if m2:
            self.log.info(f"M2: {m2.groups()}")

    def _reply(self, irc, msg, factoid, addressed=True, **more):
        '''
        Respond with a factoid.

        This is used to form almost all responses.

        >>> self._reply(irc, msg, "system-subject", extra="things")

        Or if some special factoid constructoin is neeeded:

        >>> reply = db.choose_factoid('system-subject')
        >>> self._reply(irc, msg, reply, extra="things")
        '''
        chan = msg.args[0]
        db = self.getDb(chan)

        self.log.debug(f'Bucket: _reply(msg:|[{repr(msg.args[0])}, {repr(msg.args[1])}]|, factoid:|{repr(factoid)}|)')

        if isinstance(factoid, str):
            try:
                factoid = db.choose_factoid(factoid)
            except KeyError:
                return
            self.log.debug(f'Bucket: _reply() convert factoids: {factoid}')

        if msg.channel and not db.is_system_fact(factoid[0]):
            self.hist.add_factoid(msg.channel, factoid)

        more.update(self.hist.more(msg), to=irc.nick)
        subject, link, tidbit = factoid
        tidbit = db.resolve(tidbit, **more)            
        if link.lower() == 'reply':
            irc.reply(tidbit, prefixNick=False)
            return
        if link.lower() == 'action':
            if not addressed:
                ## This is what should work but hits the assert.  val says
                ## it's a bug so maybe it can be re-enabled in a future
                ## version.
                # irc.reply(tidbit, action=True, prefixNick=False)

                ## This works around the assert but tickles Misc to throw.
                irc.noReply()
                #msg.tag('repliedTo')
                newMsg = ircmsgs.action(msg.channel or "", tidbit)# , msg=msg)
                irc.queueMsg(newMsg)
                self.log.info(f'action: queued msg to channel:{msg.channel} tidbit:{tidbit}, {msg.tags}')

            else:
                ## This work-around works for addressed
                irc.reply(tidbit, action=True, noLengthCheck=True)
                self.log.info(f'action: addressed to channel:{msg.channel} tidbit:{tidbit}, {msg.tags}')
            return
        reply = ' '.join([subject, link, tidbit])
        irc.reply(reply, prefixNick=addressed)
        self.log.info(f'{link}: to channel:{msg.channel} tidbit:{tidbit}, {msg.tags}')

    def _getUsername(self, msg):
        try:
            user = ircdb.users.getUser(msg.prefix)
        except KeyError:
            user = None
        if user:
            return user.name
        return msg.nick

    def _isCapable(self, msg, cap):
        if not msg.channel or msg.channel == 'global':
            capability = 'admin'
        else:
            capability = ircdb.makeChannelCapability(msg.channel, cap)

        tf = ircdb.checkCapability(msg.prefix, capability,
                                   ignoreDefaultAllow=True,
                                   ignoreChannelOp=True)
        self.log.debug(f'isCapable: "{msg.prefix}" in "{msg.channel}" for {capability} "{cap}" -> {tf}')
        return tf

    @wrap(['channeldb', 'text'])
    def cap(self, irc, msg, args, channel, cap):
        """[<channel>] <capability>

        Check capability function.
        """
        tf = self._isCapable(msg, 'system')
        irc.reply(f'isCapable: "{msg.prefix}" in "{msg.channel}" for "{cap}" -> {tf}')        
            
Class = Bucket


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
