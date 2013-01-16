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

import time

def divide(number, by):
    return (number / by), (number % by)
def yi_olde_timey(seconds):
    'Return (quadraels, extraraels, subraels, leftover), '
    quadraels, subraels = divide(seconds, 1753200)
    raels = quadraels * 4
    extraraels, remainder = divide(subraels, 432000)
    return quadraels, extraraels, subraels, remainder


class Tavtime(callbacks.Plugin):
    """Add the help for "@plugin help Tavtime" here
    This should describe *how* to use this plugin."""

    def yi(self, irc, msg, args):
        '''Check if it is yi or not'''
        seconds = int(time.time())
        quadraels, extraraels, subraels, remainder = yi_olde_timey(seconds)
        left = "%d and %d to go" % (3 - extraraels, 432000 - remainder)
        print 'yi:', quadraels, extraraels, subraels, remainder
        if extraraels == 4:
            irc.reply('Yes! PARTAI!', prefixNick=False)
            return
        irc.reply('Not yet... %s' % left, prefixNick=False)
        return
    yi = wrap(yi)

    def tavtime(self, irc, msg, args):
        seconds = int(time.time())
        quadraels, extraraels, subraels, remainder = yi_olde_timey(seconds)
        rep = '%s  -  It is now %d:%d:%d:%d  -  %s' % \
            (unichr(8987),
             quadraels, extraraels, subraels, remainder, 
             unichr(8986))
        rep = rep.encode('utf-8')
        irc.reply(rep, prefixNick=False)
        return

    pass


Class = Tavtime


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
