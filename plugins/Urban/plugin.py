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

ud_api_base_url = \
    'http://api.urbandictionary.com/v0/define?'

import urllib, urllib2, json
import re

def udquery(term, page=1):
    print 'URBAN: looking up term="%s", page=%d' % (term,page)

    url = ud_api_base_url + urllib.urlencode(locals())
    res = urllib2.urlopen(url)
    page = res.read()
    return json.loads(page)
    
def format_result(res, number, pat):
    defi = dict(res['list'][number-1])
    defi['number'] = number
    defi['total'] = res.get('total',len(res['list']))
    defi['pages'] = res.get('pages',0)
    defi['result_type'] = res['result_type']
    defi['has_related_words'] = res['has_related_words']

    res = pat % defi
    return re.sub('\s+',' ',res)

class Urban(callbacks.Plugin):
    """Lookup hip Internet terms"""
    threaded = True

    def __init__(self, irc):
        self.__parent = super(Urban, self)
        self.__parent.__init__(irc)
        self.cache = {}         # (term,page) -> res

    def _get(self, term, page):
        # fixme: invalidate cache once in a while
        key = (term,page)
        try:
            return self.cache[key]
        except KeyError:
            pass
        res = udquery(term,page)
        self.cache[key] = res
        return res

    def ud(self, irc, msg, args, number, term):
        term = ' '.join(term)
        page = 1                # hard code for now

        pattern = self.registryValue('resultFormat')

        try:
            res = self._get(term,page)
        except Exception, err:
            irc.reply('Sorry, urbandictionary is to hip to answer us (%s)' % err)
        res_type = res['result_type']
        nres = len(res['list'])

        #self.log.debug('%d results:' % nres)
        #for one in res['list']:
        #    self.log.debug(str(one))

        if res_type == 'no_results':
            irc.reply('No hip definition for "%s"' % term)
            return

        if number > nres:
            isare = "are"
            if nres == 1: isare = "is"
            irc.reply('There %s only %d hip (%s) definitions for "%s"' % \
                          (isare, nres, res_type, term))
            return

        if res_type in ['fulltext', 'exact']:
            irc.reply(format_result(res, number, pattern),
                      prefixNick=False)
            return
        irc.reply('Unexpected result type: "%s"' % res_type)
        return
    ud = wrap(ud, [optional('int',1), many('something')])




Class = Urban


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
