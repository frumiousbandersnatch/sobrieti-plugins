###
# Copyright (c) 2021, Frumious Bandersnatch
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

import re
from importlib import reload
from . import store
reload(store)

import supybot.ircmsgs as ircmsgs
from supybot import utils, plugins, ircutils, callbacks
from supybot.commands import *
try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('Bucket')
except ImportError:
    # Placeholder that allows to run the plugin on a bot
    # without the i18n module
    _ = lambda x: x


# msg.nick is sender nick
# msg.args[0] is channel
# msg.args[1] is message
# - if privmsg then simple text
# - if action then \x01ACTION the action\x01
# irc.nick is bot nick

class Bucket(callbacks.PluginRegexp, plugins.ChannelDBHandler):
    """Mostly compatible implementation of XKCD Bucket"""
    threaded = True
    public = True
    regexps = []
    addressedRegexps = ["isare",]
    unaddressedRegexps = ["say", "items1", "items2"]

    def __init__(self, irc):
        callbacks.PluginRegexp.__init__(self, irc)
        plugins.ChannelDBHandler.__init__(self)

    def makeDb(self, filename):
        return store.Bucket(filename)

    def say(self, irc, msg, regex):
        r"^say (?P<sentence>.*$)"
        text = regex["sentence"]
        text = text.capitalize() + "!"
        irc.reply(text, prefixNick=False)

    ### Common for items1/items2 because I do not know how to combine
    ### all three into one.
    def _itemsx(self, irc, msg, regex):
        chan = msg.args[0]
        me = regex["nick"]
        item = regex["item"]
        if me != irc.nick:
            return
        db = self.getDb(chan)
        db.item_give(item)
        max_items = self.registryValue('max_items')
        have = db.items_holding()
        if len(have) > max_items:
            old = have[0]
            db.item_drop(old)
            chirp = f'drops {old} and takes {item}'
        else:
            chirp = f'now contains {item}'
        irc.queueMsg(ircmsgs.action(chan, chirp))
        return

    # /me puts {item} in Bucket.
    # /me gives {item} to Bucket
    def items1(self, irc, msg, regex):
        r"^\x01ACTION (?:gives|puts) (?P<item>.+?) (?:to|in) (?P<nick>[^ ]+?)\x01$"
        self._itemsx(irc, msg, regex)

    # /me gives Bucket {item}
    def items2(self, irc, msg, regex):
        r"^\x01ACTION gives (?P<nick>[^ ]+) (?P<item>.+?)\x01$"
        self._itemsx(irc, msg, regex)

    def junk(self, irc, msg, regex):
        r".*"
        print("junk:")
        print(f'msg:|{msg}|')
        print(f'|{msg.args[1]}|')
        if regex:
            print(regex, regex.groups())


    def isare(self, irc, msg, regex):
        r"^(?P<key>.*) +(?P<isare>is|are) +(?P<value>.*)$"
        try:
            key = regex["key"]
            val = regex["value"]
            singular = regex["isare"] == "is"
        except IndexError:
            return

Class = Bucket


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
