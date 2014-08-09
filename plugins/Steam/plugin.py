###
# Copyright (c) 2014, Frumious Bandersnatch
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

import json
import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('Steam')
except:
    # Placeholder that allows to run the plugin on a bot
    # without the i18n module
    _ = lambda x:x

class Steam(callbacks.Plugin):
    """Interact with the Steam game service."""
    threaded = True

    # http://steamcommunity.com/dev
    query_url = "http://api.steampowered.com/%(interface)s/%(method)s/v%(version)04d/?key=%(apikey)s&format=json"


    def _call(self, method="GetPlayerSummaries", version=2, interface="ISteamUser", apikey=None, **kwds):
        apikey = apikey or self.registryValue('apikey')
        if not apikey:
            return 
        url = self.query_url % locals()
        extra = ['%s=%s' % kv for kv in kwds.items()]
        if extra:
            url += '&' + '&'.join(extra)
        self.log.debug(url)
        page = utils.web.getUrl(url)
        return json.loads(page)
        
            
    def _steamid(self, vanity):
        dat = self._call("ResolveVanityURL", version=1, vanityurl=vanity)
        try:
            return dat['response']['steamid']
        except TypeError:
            return
        except KeyError:
            return

    def steamid(self, irc, msg, args, channel, name):
        '''[<steamname>]

        Print the Steam ID associated with the steam "vanity" name.
        '''
        name = name or msg.nick
        sid = self._steamid(name)

        if not sid:
            return irc.reply('steam does know %s' % name)
        return irc.reply('%s has steam ID %s' % (name, sid))
        
    steamid = wrap(steamid, ['channel', optional(first('otherUser','something'))])


Class = Steam


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
