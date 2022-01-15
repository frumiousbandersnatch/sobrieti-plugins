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
from importlib import reload
from . import nordl
reload(nordl)

from collections import defaultdict

import os
mydir = os.path.dirname(__file__)

class Nordl(callbacks.Plugin):
    """An n-char implementation of wordle"""

    def __init__(self, irc):
        self.__parent = super(Nordl, self)
        self.__parent.__init__(irc)
        # map from tuple(channel,nick)
        self._games = dict()
        # fixme: make persistent, history, leaderboard....

    def _get_game(self, irc, msg, channel):
        key = (channel, msg.nick)
        try:
            return self._games[key]
        except KeyError:
            irc.reply(f'No past nor existing nordl game for {key}, try "start" command')
            raise

    def _play(self, irc, msg, channel, guess):
        'One play of the game with reply'
        try:
            game = self._get_game(irc, msg, channel)
        except KeyError:
            return

        yn, line = game.guess(guess)
        if yn:
            rep = f'{line} got it in {len(game)}!'
        else:
            rep = f'{line} #{len(game)}'
        irc.reply(rep)

    @wrap(['channelDb', optional("int", 5), optional("something", "")])
    def start(self, irc, msg, args, channel, length, guess):
        '''[length] [first-guess]

        Start a nordl game.  Give number for word length, default is 5.
        '''
        length = max(2, min(9,length))
        text = random.choice(open(f'{mydir}/words-{length}').read().split('\n'))
        game = nordl.Game(text, 'dark')
        key = (channel, msg.nick)
        self._games[key] = game
        if guess:
            self._play(irc, msg, channel, guess)
            return
        irc.reply(f'guess {length} letter words with the "guess" command.  good luck! ({channel},{msg.nick})')
        
    @wrap(['channelDb'])
    def board(self, irc, msg, args, channel):
        '''
        Show the full board of your last game'''

        try:
            game = self._get_game(irc, msg, channel)
        except KeyError:
            return

        for count, (yn, line) in enumerate(game.board()):
            irc.reply(f'{line} #{count}', prefixNick = False)

    @wrap(['channelDb', 'something'])
    def guess(self, irc, msg, args, channel, guess):
        '''<word>
        
        Guess a word in an ongoing game'''
        self._play(irc, msg, channel, guess)
        
    @wrap(['channelDb'])
    def giveup(self, irc, msg, args, channel):
        '''
        Bail on a game and learn the word'''
        try:
            game = self._get_game(irc, msg, channel)
        except KeyError:
            return

        irc.reply(f'The word was "{game._word}"')


Class = Nordl


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
