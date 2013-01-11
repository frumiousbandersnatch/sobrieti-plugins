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

# ripped out of original sobrieti/jenni/phenny with much ugliness

import web

class Grab(web.urllib.URLopener):
    def __init__(self, *args):
        self.version = 'Mozilla/5.0 (Jenni)'
        web.urllib.URLopener.__init__(self, *args)
        self.addheader('Referer', 'https://github.com/myano/jenni')
    def http_error_default(self, url, fp, errcode, errmsg, headers):
        return web.urllib.addinfourl(fp, [headers, errcode], "http:" + url)

def google_ajax(query):
    """Search using AjaxSearch, and return its JSON."""
    if isinstance(query, unicode):
        query = query.encode('utf-8')
    uri = 'http://ajax.googleapis.com/ajax/services/search/web'
    args = '?v=1.0&safe=off&q=' + web.urllib.quote(query)
    handler = web.urllib._urlopener
    web.urllib._urlopener = Grab()
    bytes = web.get(uri + args)
    web.urllib._urlopener = handler
    return web.json(bytes)

def google_search(query):
    results = google_ajax(query)
    try: return results['responseData']['results'][0]['unescapedUrl']
    except IndexError: return None
    except TypeError:
        print results
        return False

def google_count(query):
    results = google_ajax(query)
    if not results.has_key('responseData'): return '0'
    if not results['responseData'].has_key('cursor'): return '0'
    if not results['responseData']['cursor'].has_key('estimatedResultCount'):
        return '0'
    return results['responseData']['cursor']['estimatedResultCount']

def formatnumber(n):
    """Format a number with beautiful commas."""
    parts = list(str(n))
    for i in range((len(parts) - 3), 0, -3):
        parts.insert(i, ',')
    return ''.join(parts)

class Goo(callbacks.Plugin):
    """Add the help for "@plugin help Goo" here
    This should describe *how* to use this plugin."""
    threaded = True

    def gc(self, irc, msg, args, query):
        'Google count'
        query = ' '.join(query)
        if not query:
            return
        query = query.encode('utf-8')
        num = formatnumber(google_count(query))
        irc.reply(query + ': ' + num)
        return
    gc = wrap(gc, [many('something')])


    def gcalc(self, irc, msg, args, expression):
        """Google calculator."""
        expression = ' '.join(expression)

        q = expression.encode('utf-8')
        q = q.replace('\xcf\x95', 'phi') # utf-8 U+03D5
        q = q.replace('\xcf\x80', 'pi') # utf-8 U+03C0
        uri = 'http://www.google.com/ig/calculator?q='
        bytes = web.get(uri + web.urllib.quote(q))
        parts = bytes.split('",')
        answer = [p for p in parts if p.startswith('rhs: "')][0][6:]
        if not answer:
            irc.reply('Sorry, no result.')
            return

        answer = answer.decode('unicode-escape')
        answer = ''.join(chr(ord(c)) for c in answer)
        answer = answer.decode('utf-8')
        answer = answer.replace(u'\xc2\xa0', ',')
        answer = answer.replace('<sup>', '^(')
        answer = answer.replace('</sup>', ')')
        answer = web.decode(answer)
        irc.reply(answer)
        return
    gcalc = wrap(gcalc, [many('something')])


Class = Goo


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
