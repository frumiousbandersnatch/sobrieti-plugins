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
from enum import Enum

_ = PluginInternationalization('Stopwatch')

def tfmt(dt):
    '''
    Return string rep of a duration in seconds.
    '''
    hours = int(dt // 3600)
    minutes = int((dt % 3600) // 60)
    seconds = int(dt % 60)
    return f'{hours}:{minutes:02}:{seconds:02}'

class State(Enum):
    """State machine states."""
    READY = 1
    RUNNING = 2
    PAUSED = 3
    STOPPED = 4

class Timer:
    def __init__(self):
        self.state = State.READY
        self.accrued = 0        # add to this when paused
        self.started = None     # when running started

    @property
    def since(self):
        if self.started is None:
            return
        return time.time() - self.started

    def __str__(self):
        if self.state == State.READY:
            return f'ready'

        if self.state == State.RUNNING:
            t = self.accrued + self.since
            return f'{tfmt(t)} (running)'

        if self.state == State.PAUSED:
            return f'{tfmt(self.accrued)} (paused)'

        if self.state == State.STOPPED:
            return f'{tfmt(self.accrued)} (stopped)'

        raise ValueError(f'illegal state: {self.state}')

    def __repr__(self):
        return str(self)

    def start(self):
        """Transition from READY to RUNNING."""
        if self.state == State.READY:
            self.state = State.RUNNING
            self.accrued = 0
            self.started = time.time()
            return str(self)
        else:
            return f"cannot start in state {self.state.name}"

    def pause(self):
        """Transition from RUNNING to PAUSED."""
        if self.state == State.RUNNING:
            self.state = State.PAUSED
            self.accrued += time.time() - self.started
            self.started = None
            return str(self)
        elif self.state == State.PAUSED:
            return str(self)
        else:
            return f"cannot pause in state {self.state.name}"

    def resume(self):
        """Transition from PAUSED to RUNNING."""
        if self.state == State.PAUSED:
            self.state = State.RUNNING
            self.started = time.time()
            return str(self)
        elif self.state == State.RUNNING:
            return str(self)
        else:
            return f"cannot resume in state {self.state.name}"

    def stop(self):
        """Transition from RUNNING to STOPPED."""
        if self.state == State.RUNNING or self.state == State.PAUSED:
            self.state = State.STOPPED
            if self.started:
                self.accrued += time.time() - self.started
            self.started = None
            return str(self)
        elif self.state == State.STOPPED:
            return str(self)
        else:
            return f"cannot stop in state {self.state.name}"

    def reset(self):
        """Transition from STOPPED to READY."""
        if self.state in (State.STOPPED, State.RUNNING, State.PAUSED):
            self.state = State.READY
            self.accrued = 0
            self.started = None
            return str(self)
        elif self.state == State.READY:
            return str(self)
        else:
            return f"cannot reset in state {self.state.name}"
    

class Stopwatch(callbacks.Plugin):
    """Maintain stopwatch timers"""
    def __init__(self, irc):
        super().__init__(irc)
        self.channel_timers = defaultdict(dict)

    def _get(self, channel, name):
        timers = self.channel_timers[channel]
        if name in timers:
            return timers[name]
        timer = Timer()
        timers[name] = timer
        return timer

    def start(self, irc, msg, args, channel, name):
        """[<channel> <name>]

        Start the stopwatch.
        """
        timer = self._get(channel, name)
        irc.reply(f'{name}: {timer.start()}')
    start = wrap(start, ['channel', 'something'])

    def stop(self, irc, msg, args, channel, name):
        """[<channel> <name>]

        Stop the stopwatch and display elapsed time.
        """
        timer = self._get(channel, name)
        irc.reply(f'{name}: {timer.stop()}')
    stop = wrap(stop, ['channel', 'something'])

    def pause(self, irc, msg, args, channel, name):
        """[<channel> <name>]

        Puase the stopwatch and display elapsed time.
        """
        timer = self._get(channel, name)
        irc.reply(f'{name}: {timer.pause()}')
    pause = wrap(pause, ['channel', 'something'])

    def resume(self, irc, msg, args, channel, name):
        """[<channel> <name>]

        Resume a paused stopwatch and display elapsed time.
        """
        timer = self._get(channel, name)
        irc.reply(f'{name}: {timer.resume()}')
    resume = wrap(resume, ['channel', 'something'])

    def reset(self, irc, msg, args, channel, name):
        """[<channel> <name>]

        Reset a stopwatch and display elapsed time.
        """
        timer = self._get(channel, name)
        irc.reply(f'{name}: {timer.reset()}')
    reset = wrap(reset, ['channel', 'something'])

    def remove(self, irc, msg, args, channel, name):
        """[<channel> <name>]

        Reove a stopwatch and display elapsed time.
        """
        timers = self.channel_timers[channel]
        if name in timers:
            timer = timers[name]
            del (timers[name])
            irc.reply(f'{name}: {timer} (removed)')
            return
        irc.reply(f'no timer to remove: {name}')
    remove = wrap(remove, ['channel', 'something'])
    
    def lap(self, irc, msg, args, channel, name):
        """[<channel> <name>]

        Display current elapsed time without stopping the stopwatch.
        """
        timer = self._get(channel, name)
        irc.reply(f'{name}: {timer}')
    lap = wrap(lap, ['channel', 'something'])

    def show(self, irc, msg, args, channel):
        """[<channel>]

        List all running timers.
        """
        answer = list()
        for name, timer in self.channel_timers[channel].items():
            answer.append(f'{name}: {timer}')
        if not answer:
            irc.reply("no timers defined")
            return
        irc.reply(', '.join(answer))
    show = wrap(show, ['channel'])



Class = Stopwatch


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
