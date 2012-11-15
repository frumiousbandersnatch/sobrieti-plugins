###
# Copyright (c) 2012, Frumious Bandersnatch
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

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

import supybot.dbi as dbi

import re, random
optRe = re.compile(r'({\d})')

class PosNegRecord(dbi.Record):
    __fields__ = [
        'pn',             # positive ('+') or negative ('-') statement
        'pattern',        # the string to apply
        'number',         # number of people this string is for
        ]
    pass

def en_join(args):
    if len(args) < 2:
        return ' '.join(args)

    if len(args) < 3:
        return ' and '.join(args)

    return ', '.join(args[:-1]) + ' and ' + args[-1]

class PosNeg(callbacks.Plugin, plugins.ChannelDBHandler):
    """Various positive/negative reinforcements.

    A reinforcement should contain one or more numerical placeholders
    like {0}, {1}, etc which will match the things that it is
    eventually called with.
    """

    def __init__(self, irc):
        callbacks.Plugin.__init__(self, irc)
        plugins.ChannelDBHandler.__init__(self, irc)
        return

    def makeDb(self, filename):
        return dbi.DB(filename, Record=PosNegRecord)

    def stats(self, irc, msg, args, channel):
        """[<channel>]

        Report some statistics"""
        db = self.getDb(channel)
        np = nm = 0
        maxn = 0
        for rec in db:
            if rec.pn == '+': np += 1
            if rec.pn == '-': nm += 1
            if rec.number > maxn: maxn = rec.number
        irc.reply('I have %d positive and %d negative reinforcements for up to %d things' \
                      % (np, nm, maxn))
        return
    stats = wrap(stats, ['channel'])
            


    def _resolve(self, channel, pn, names):
        'Resolve the message.'
        number = len(names)
        db = self.getDb(channel)
        def find(r): 
            return (r.pn == pn and r.number == number)
        choose_from = [x for x in db.select(find)]
        if not choose_from:
            return
        res = random.choice(choose_from)
        print 'PosNeg:'
        print res.pattern
        print names
        return res.pattern.format(*names)

    def hate(self, irc, msg, args, channel, things):
        """[<channel>] <things>

        Apply some negative reinforcement to <things> in <channel>.
        """
        msg = self._resolve(channel, '-', things)
        if msg:
            irc.reply(msg, action = True)
            return
        irc.reply("I don't know nothing negative about %s" % en_join(things))
        return
    hate = wrap(hate, ['channel', many('something')])
    slap = hate

    def love(self, irc, msg, args, channel, things):
        """[<channel>] <things>

        Apply some positive reinforcement to <things> in <channel>.
        """
        msg = self._resolve(channel, '+', things)
        print things, msg
        if msg:
            irc.reply(msg, action = True)
            return
        irc.reply("Sorry, I have no love for %s" % en_join(things))
        return
    love = wrap(love, ['channel', many('something')])

    def _wash(self, pattern, irc):
        """Return (nthings,pattern) if pattern is okay"""

        pattern = ' '.join(pattern)
        phs = optRe.findall(pattern)
        if not phs:
            irc.reply('Pattern has no place holders.  Use "{0}", "{1}", etc to match first, second, etc, thing')
            return

        try:
            nums = [int(ph[1:-1]) for ph in phs]
        except ValueError:
            irc.reply('Pattern place holders need to be integer numbers')
            return

        nthings = max(nums)+1
        return nthings, pattern

    def add(self, irc, msg, args, channel, pn, pattern):
        """[<channel] +/- <pattern> 

        Add a positive or negative reinforcement pattern containing
        one or more {0}, {1}, etc place holders."""
        
        nthings, pattern = self._wash(pattern, irc)
        db = self.getDb(channel)
        rec = PosNegRecord(pn = pn, pattern = pattern, number = nthings)
        ident = db.add(rec)
        irc.reply('Added "%s" pattern for %d things at ID #%d' % \
                      (pn, nthings, ident))
        return
    add = wrap(add, ['channel', ('literal', ('+','-')), many('something')])

    # update an id
    def replace(self, irc, msg, args, channel, ident, pn, pattern):
        """[<channel>] <ID#> [+/-] <pattern>

        Replace a reinforcement pattern of given <ID#> optionally setting 
        if it is positive or negative."""
        ok = self._wash(pattern, irc)
        if not ok: return
        nthings, pattern = ok

        db = self.getDb(channel)
        rec = db.get(ident)
        if not pn:
            pn = rec.pn

        newrec = PosNegRecord(pn = pn, pattern = pattern, number = nthings)
        db.set(ident, newrec)
        irc.reply('Updated %s reinforcement ID #%d for %d things to be: "%s"' \
                      % (pn, ident, nthings, pattern))
        return
    replace = wrap(replace, ['channel', 'int', 
                             optional(('literal', ('+','-'))),
                             many('something')])

    pass


Class = PosNeg


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
