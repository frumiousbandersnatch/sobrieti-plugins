###
# Copyright (c) 2022, Frumious Bandersnatch
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

from supybot import utils, plugins, ircutils, callbacks, ircmsgs, conf
from supybot.commands import *
try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('Comic')
except ImportError:
    # Placeholder that allows to run the plugin on a bot
    # without the i18n module
    _ = lambda x: x

from io import BytesIO
from importlib import reload
from . import comic
from . import history 
from . import publish 
# reload for live developing/debugging
reload(comic)
reload(history)
reload(publish)

class Comic(callbacks.Plugin):
    """Comic generation feature from WeedBot of yore"""
    threaded = True

    recent = history.DB()
    datadir = conf.supybot.directories.data.dirize("comic")

    def doPrivmsg(self, irc, msg):
        if ircmsgs.isCtcp(msg) and not ircmsgs.isAction(msg):
            return
        if not msg.channel:
            return
        text = ircmsgs.prettyPrint(msg, showNick=False)
        #self.log.info(f'remember: {msg.nick} {msg.channel} {irc.network} {text}')
        self.recent.remember(msg.nick, text, msg.channel, irc.network)

    @wrap(['channelDb'])
    def comic(self, irc, msg, args, channel):
        '''[<channel>]

        Render a comic from recent chat
        '''
        events = self.recent.recall(msg.channel, irc.network)
        if not events:
            irc.reply("too quiet, no funnies")
            return

        panels = comic.make_panels(events)
        im = comic.make_comic(panels, self.datadir)
        dat = BytesIO()
        im.save(dat, "JPEG")
        dat.seek(0)
        rep = publish.post(dat)
        irc.reply(rep)

Class = Comic


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
