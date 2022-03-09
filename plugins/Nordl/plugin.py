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

from supybot import utils, plugins, ircutils, callbacks
from supybot.commands import *
try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('Nordl')
except ImportError:
    # Placeholder that allows to run the plugin on a bot
    # without the i18n module
    _ = lambda x: x

import random
from . import nordl
from importlib import reload as reload_module
reload_module(nordl)

from collections import defaultdict

import os
mydir = os.path.dirname(__file__)

class Nordl(callbacks.Plugin, plugins.ChannelDBHandler):
    """An n-char implementation of wordle"""
    threaded = True
    public = True

    def __init__(self, irc):
        callbacks.Plugin.__init__(self, irc)
        plugins.ChannelDBHandler.__init__(self)
        # map from tuple(channel,nick)
        self._games = dict()
        # fixme: make persistent, history, leaderboard....

    def makeDb(self, filename):
        return nordl.Field(filename)


    @wrap(['channelDb', optional("int", 5)])
    def start(self, irc, msg, args, channel, length):
        '''[length]

        Start a nordl game.  Give number for word length, default is 5 letters.
        '''
        nf = self.getDb(channel)

        length = max(2, min(18,length))
        n, c = msg.nick, msg.channel or ""
        # if who:
        #     n, c = "*", "*"
        gid = nf.start(length, n, c)
        irc.reply(f'Start nordl game #{gid}. Guess a word with {length} letters.  Good luck!')
        
    @wrap(['channelDb', optional('int')])
    def board(self, irc, msg, args, channel, gid):
        '''[<chanel> <gameid>]

        Show the full board of your last game or a specific game number
        '''

        nf = self.getDb(channel)

        if gid is None:
            try:
                gid = nf.last(msg.nick, msg.channel or "")
            except IndexError:
                irc.reply(f'no recent game for you in channel "{channel}"')
                return

        try:
            gd = nf.game_data(gid)
        except IndexError:
            irc.reply(f'no recent game for you in channel "{channel}"')
            return

        oc, gs = gd
        lastnick = ""
        for count, (guess, nick, _, _) in enumerate(gs):
            lastnick = nick
            if count == 0:
                answer = guess
                continue
            codes = nordl.codify(guess, answer)
            line = nordl.markdup(guess, codes, 'dark')
            line += f' [{count}] {nick}'
            irc.reply(line, prefixNick=False)
        if oc is None:
            irc.reply(f'game {gid} is still open', prefixNick=False)
        elif oc:
            irc.reply(f'game {gid} won by {lastnick}!', prefixNick=False)
        else:
            codes = nordl.codify(answer, answer)
            line = nordl.markdup(answer, codes, 'dark')
            line += f' game {gid} was given up'
            irc.reply(line, prefixNick=False)


    @wrap(['channelDb', 'something', optional('int')])
    def guess(self, irc, msg, args, channel, guess, gid):
        '''<word>
        
        Guess a word in an ongoing game.
        '''
        nf = self.getDb(channel)

        if gid is None:
            try:
                gid = nf.last(msg.nick, msg.channel or "")
            except IndexError:
                irc.reply(f'no recent game for you in channel "{channel}"')
                return

        try:
            gotit = nf.guess(gid, guess, msg.nick, msg.channel or "")
        except IndexError as err:
            irc.reply(str(err))
            return

        answer = nf.answer(gid)
        codes = nordl.codify(guess, answer)
        line = nordl.markdup(guess, codes, 'dark')

        if gotit:
            irc.reply(f'{line} Correct!')
        else:
            irc.reply(f'{line}')

    @wrap(['channelDb'])
    def giveup(self, irc, msg, args, channel):
        '''
        Bail on a game and learn the word.
        '''
        nf = self.getDb(channel)

        try:
            gid = nf.last(msg.nick, msg.channel or "")
        except IndexError:
            irc.reply(f'no recent game for you in channel "{channel}"')
            return

        try:
            answer = nf.giveup(gid, msg.nick, msg.channel or "")
        except IndexError:
            irc.reply(f'you can not give up game {gid}, already over or it is not yours')
            return
        irc.reply(f'the answer was "{answer}".  Better luck next time!')

    @wrap(['channelDb'])
    def scores(self, irc, msg, args, channel):
        '''[channel]
        Show top scores.
        '''
        nf = self.getDb(channel)
        top = list()
        all_scores = nf.scores(msg.channel or "")
        print(all_scores)
        for n, (g, c) in all_scores.items():
            if g <= 0:
                continue
            pc = int(100.0*c/g)
            top.append((-pc, f'{n}: {pc}% [{c}/{g}] '))
        if not top:
            irc.reply('no nordl game results yet, try "start"')
            return
        top.sort()
        top = [t[1] for t in top]
        line = ', '.join(top[:10])
        irc.reply(line, prefixNick=False)
        
        

Class = Nordl


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
