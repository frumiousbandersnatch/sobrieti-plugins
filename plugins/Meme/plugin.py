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
from supybot.i18n import PluginInternationalization, internationalizeDocstring
import urllib
from urllib2 import urlopen
import json
from BeautifulSoup import BeautifulSoup

_ = PluginInternationalization('Meme')


@internationalizeDocstring
class Meme(callbacks.Plugin):
    """Add the help for "@plugin help Meme" here
    This should describe *how* to use this plugin."""
    threaded = True

    def _am(self, irc, params = ""):
        url = 'http://api.automeme.net/text?lines=1'
        if params:
            url = '&'.join([url,params])
        res = urlopen(url)
        page = res.read().strip()
        irc.reply(page, prefixNick=False)
        return

    def automeme(self, irc, msg, args):
        'Generate a meme.'
        self._am(irc)
    automeme = wrap(automeme, )

    def hipster(self, irc, msg, args):
        'Generate a meme of the hipster persuasion.'
        self._am(irc,'vocab=hipster')
    hipster = wrap(hipster, )

    ### this is very insulting
    # def insult(self, irc, msg, args):
    #     'Generate an insult'
    #     page = urlopen('http://www.insultgenerator.org').read()
    #     soup =  BeautifulSoup(page)
    #     baka = soup.find('table').find('td').text
    #     irc.reply(baka, prefixNick=False)
    #     return


    def search(self, irc, msg, args, term, maxHits):
        '''<term> [maxnumber=10]

        Search for meme images.
        '''
        self.log.debug('Meme.search: "%s"' % term)
        cmd = 'Generators_Search'
        urlbase = "http://version1.api.memegenerator.net/%s?%s"
        url = urlbase % (cmd, urllib.urlencode({'q':term,
                                                'pageIndex':0,
                                                'pageSize':maxHits}))
        self.log.debug('Meme.search: url: %s' % url)
        res = json.loads(urlopen(url).read())
        if not res['success']:
            irc.reply('Failed to search for "%s"' % (term,))
            return

        r = res['result']
        if not len(r):
            irc.reply('Search for "%s" returned no results' % (term,))
            return
            
        data = []
        for ret in r:
            data.append((ret['totalVotesScore'], ret['displayName'], ret['imageUrl']))
        data.sort()
        data.reverse()
        msg = []
        for d in data:
            msg.append(('%s: <%s>' % (d[1],d[2])))
        irc.reply(' | '.join(msg), prefixNick=False)
        return
    search = wrap(search, ['something', optional('int',10)])

        


Class = Meme


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
