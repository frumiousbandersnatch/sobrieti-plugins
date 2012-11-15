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


class ScoreRecord(dbi.Record):
    __fields__ = [
        'thing',                # thing getting scored
        'ups',                  # number of up votes
        'downs',                # number of down votes
        ]
    pass


def en_join(*args):
    if len(args) < 2:
        return ' '.join(args)

    if len(args) < 3:
        return ' and '.join(args)

    return ', '.join(args[:-1]) + ' and ' + args[-1]

class Scores(callbacks.Plugin, plugins.ChannelDBHandler):
    """Keep anonymous and meaningless up and down votes on things."""

    def __init__(self, irc):
        callbacks.Plugin.__init__(self, irc)
        plugins.ChannelDBHandler.__init__(self, irc)
        return

    def makeDb(self, filename):
        return dbi.DB(filename, Record=ScoreRecord)


    def stats(self, irc, msg, args, channel, order):
        """[<channel>] 

        Show the <channel>'s scores stats.
        """
        db = self.getDb(channel)
        res = [x for x in db]

        print order
        sortf = {
            'low': lambda a,b: (a.ups-a.downs) - (b.ups-b.downs),
            'high': lambda a,b: (b.ups-b.downs) - (a.ups-a.downs),
            }
        sorter = sortf[order]
        res.sort(sorter)
        res = ['%s:[%d-%d=%d]'%(x.thing,x.ups,x.downs,x.ups-x.downs) \
                   for x in res]
        res = en_join(*res)
        irc.reply('%s scores in %s: %s' % (order.capitalize(), channel, res))
        return
    stats = wrap(stats, ['channel', 
                         optional(('literal', ('low','high')), 'high')])

    def _get(self, channel, thing):
        'Get record for thing in channel.'
        if isinstance(thing, list): thing = ' '.join(thing)
        db = self.getDb(channel)
        res = [x for x in db.select(lambda r: r.thing == thing)]
        if not res:
            res = ScoreRecord(thing=thing,ups=0,downs=0)
            ident = db.add(res)
            res = [res]
        return res[0]

    def _score(self, irc, msg, args, channel, thing):
        """[<channel>] <thing>

        Display thing's score
        """
        if isinstance(thing, list): thing = ' '.join(thing)

        res = self._get(channel,thing)
        tot = res.ups - res.downs
        irc.reply('"%s" has score +%d/-%d (%d) in %s' % \
                      (thing, res.ups, res.downs, tot, channel))
        return
    score = wrap(_score, ['channel', many('something')])

    def addpoint(self, irc, msg, args, channel, thing):
        """[<channel>] <thing> 

        Add a point to the <thing>'s score in <channel>.
        """
        if isinstance(thing, list): thing = ' '.join(thing)

        res = self._get(channel,thing)
        res.ups += 1
        self.getDb(channel).set(res.id, res)
        #print 'SCORES:', res.id, res
        #print self.getDb(channel).map
        self._score(irc, msg, args, channel, thing)
        return
    addpoint = wrap(addpoint, ['channel', many('something')])

    def rmpoint(self, irc, msg, args, channel, thing):
        """[<channel>] <thing>

        Remove a point from the <thing>'s score in <channel>.
        """
        if isinstance(thing, list): thing = ' '.join(thing)

        res = self._get(channel, thing)
        res.downs += 1
        self.getDb(channel).set(res.id, res)
        self._score(irc, msg, args, channel, thing)
        return
    rmpoint = wrap(rmpoint, ['channel', many('something')])

    def setpoint(self, irc, msg, args, channel, up, down, thing):
        """[<channel>] +<up> -<down> <thing>

        Set the <thing>'s <up> and <down> points in <channel>.
        """
        if isinstance(thing, list): thing = ' '.join(thing)

        res = self._get(channel, thing)
        res.ups = up
        res.downs = down
        self.getDb(channel).set(res.id, res)
        self._score(irc, msg, args, channel, thing)
        return
    setpoint = wrap(setpoint, 
                    ['channel',
                     ('int', 'non-negative number', lambda x: x >= 0),
                     ('int', 'non-negative number', lambda x: x >= 0),
                     many('something')])



    pass


Class = Scores


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
