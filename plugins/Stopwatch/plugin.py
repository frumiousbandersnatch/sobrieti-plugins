###
# Copyright (c) 2025, Frumious Bandersnatch
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
from supybot.i18n import PluginInternationalization

from collections import defaultdict

import time

_ = PluginInternationalization('Stopwatch')

def tfmt(then):
    '''
    Return string rep of time since then to now
    '''
    now = time.time()
    dt = now - then
    hours = int(dt // 3600)
    minutes = int((dt % 3600) // 60)
    seconds = int(dt % 60)
    return f'{hours}:{minutes:02}:{seconds:02}'


class Stopwatch(callbacks.Plugin):
    """Maintain stopwatch timers"""
    def __init__(self, irc):
        super().__init__(irc)
        self.channel_timers = defaultdict(dict)

    def start(self, irc, msg, args, channel, name):
        """[<channel> <name>]

        Start the stopwatch.
        """
        timers = self.channel_timers[channel]
        if name in timers:
            old_time = timers[name]
            timers[name] = time.time()
            irc.reply(f'restarted timer "{name}" (was {tfmt(old_time)}')
            return
        timers[name] = time.time()
        irc.reply(f'started timer "{name}"')
    start = wrap(start, ['channel', 'something'])


    def stop(self, irc, msg, args, channel, name):
        """[<channel> <name>]

        Stop the stopwatch and display elapsed time.
        """
        timers = self.channel_timers[channel]
        if name in timers:
            old_time = timers[name]
            del (timers[name])
            irc.reply(f'stopped timer "{name}" after {tfmt(old_time)}')
            return
        irc.reply(f'no timer "{name}"')
    stop = wrap(stop, ['channel', 'something'])

    def lap(self, irc, msg, args, channel, name):
        """[<channel> <name>]

        Display current elapsed time without stopping the stopwatch.
        """
        timers = self.channel_timers[channel]
        if name in timers:
            t = timers[name]
            irc.reply(f'{tfmt(t)} "{name}"')
            return
        irc.reply(f'no timer "{name}"')
    lap = wrap(lap, ['channel', 'something'])

    def show(self, irc, msg, args, channel):
        """[<channel>]

        List all running timers.
        """
        timers = self.channel_timers[channel]
        if not timers:
            irc.reply("no timers started")
            return
        answer = []
        for name, tim in timers.items():
            answer.append(f'{tfmt(tim)} "{name}"')
        irc.reply(', '.join(answer))
    show = wrap(show, ['channel'])



Class = Stopwatch


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
