###
# Copyright (c) 2013, Frumious Bandersnatch
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

import qdbapi
reload (qdbapi)

class Qdb(callbacks.Plugin):
    """Add the help for "@plugin help Qdb" here
    This should describe *how* to use this plugin."""
    threaded = True

    def _apicall(self, irc, cmd, **kwds):
        data = qdbapi.apicall(cmd, **kwds)
        if not data:
            irc.reply('(none)')
            return
        if isinstance(data,str):
            irc.reply(data)
            return

        if isinstance(data,list):
            q = qdbapi.format_quote_list(data)
        else:
            q = qdbapi.format_quote(data)
        irc.reply(q, prefixNick=False)
        return

    def qdb(self, irc, msg, args, number):
        '''[<number>]

        Display the numbered quote.  If no number is given, display a
        random quote.
        '''
        if not number:
            self._apicall(irc,'random')
            return
        self._apicall(irc, 'get', qid=number)
        return
    qdb = wrap(qdb, [optional('int',0)])

    def random(self, irc, msg, args):
        '''Display a random quote'''
        self._apicall(irc, 'random')
    random = wrap(random)

    def get(self, irc, msg, args, number):
        '''<number>

        Display the numbered quote.
        '''
        self._apicall(irc, 'get', qid=number)
        return
    get = wrap(get,['int'])
        
    def search(self, irc, msg, args, pattern):
        '''<search pattern>

        Search the quote database.
        '''
        self._apicall(irc, 'search', pattern=pattern)
        return
    search = wrap(search,['anything'])

    def queue(self, irc, msg, args):
        '''Display the quote moderation queue.'''
        self._apicall(irc, 'queue')
        return
    queue = wrap(queue)

    def last(self, irc, msg, args):
        '''Display the last quote added.'''
        self._apicall(irc, 'last')
        return
    last = wrap(last)

    def add(self, irc, msg, args, quote):
        '''<quote>

        Add the quote to the database.  It is best to type "<nick>"
        before a line to indicate the speaker.  Lines can be separated
        with the bar "|" symbol.'''
        print 'ADD',quote
        quote = ' '.join(quote)
        quote = qdbapi.wash_quote(quote)
        data = qdbapi.apicall('add', quote=quote)
        try:
            idn = data['id']
        except IndexError:
            irc.reply('Did not get a quote ID# back, server crapped out: %s' % \
                          qdbapi.rashurl)
            return
        irc.reply('Added quote #%s' % data['id'], prefixNick=False)
        return
    add = wrap(add, [many('something')])

Class = Qdb


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

