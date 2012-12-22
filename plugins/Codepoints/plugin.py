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


import re, unicodedata
from itertools import islice

def about(u, cp=None, name=None):
    if cp is None:
        cp = ord(u)
    if name is None:
        try: name = unicodedata.name(u)
        except ValueError:
            return 'U+%04X (No name found)' % cp

    if not unicodedata.combining(u):
        template = 'U+%04X %s (%s)'
    else: template = 'U+%04X %s (\xe2\x97\x8c%s)'
    return template % (cp, name, u.encode('utf-8'))

def codepoint_simple(arg):
    arg = arg.upper()

    r_label = re.compile('\\b' + arg.replace(' ', '.*\\b') + '\\b')

    results = []
    for cp in xrange(0xFFFF):
        u = unichr(cp)
        try: name = unicodedata.name(u)
        except ValueError: continue

        if r_label.search(name):
            results.append((len(name), u, cp, name))
    if not results:
        r_label = re.compile('\\b' + arg.replace(' ', '.*\\b'))
        for cp in xrange(0xFFFF):
            u = unichr(cp)
            try: name = unicodedata.name(u)
            except ValueError: continue

            if r_label.search(name):
                results.append((len(name), u, cp, name))

    if not results:
        return None

    length, u, cp, name = sorted(results)[0]
    return about(u, cp, name)

def codepoint_extended(arg):
    arg = arg.upper()
    try: r_search = re.compile(arg)
    except: raise ValueError('Broken regexp: %r' % arg)

    for cp in xrange(1, 0x10FFFF):
        u = unichr(cp)
        name = unicodedata.name(u, '-')

        if r_search.search(name):
            yield about(u, cp, name)


def reply_results(irc, query, results, number = None):
    results = [r for r in results] # generate
    nresults = len(results)

    if not nresults:
        irc.reply('No codepoints for query "%s"' % query)
        return

    if number is not None and (number < 1 or number > nresults):
        irc.reply('No codepoint #%d for query %s (found %d)' % \
                      (number, query, nresults))
        return

    begin = 0
    end = len(results)
    if number is not None:
        begin = number - 1
        end = number

    res = ['[%d] %s, '%(c+begin+1,e) for c,e in enumerate(results[begin:end])]
    irc.reply(''.join(res))
    return


class Codepoints(callbacks.Plugin):
    """Add the help for "@plugin help Codepoints" here
    This should describe *how* to use this plugin."""

    def u(self, irc, msg, args, ch, number):
        '''<something>

        Search for something in unicode land.'''


        if set(ch.upper()) - set(
            'ABCDEFGHIJKLMNOPQRSTUVWYXYZ0123456789- .?+*{}[]\\/^$'):
            printable = False
        elif len(ch) > 1:
            printable = True
        else: printable = False

        if printable:
            reply_results(irc, ch, codepoint_extended(ch), number)
            return
        else:
            text = ch.decode('utf-8')
            # look up less than three podecoints
            if len(text) <= 3:
                for u in text:
                    irc.reply(about(u), prefixNick=False)
            # look up more than three podecoints
            elif len(text) <= 10:
                irc.reply(' '.join('U+%04X' % ord(c) for c in text), 
                          prefixNick=False)
            else: 
                irc.reply('Sorry, your input is too long!')

        return
    u = wrap(u, ['something',optional('int')])

    pass


Class = Codepoints


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
