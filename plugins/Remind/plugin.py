###
# Copyright (c) 2011, Rebecca Bettencourt
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

import time
import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.schedule as schedule
import supybot.callbacks as callbacks

class Remind(callbacks.Plugin):
    """This plugin contains commands for scheduling reminders to be posted at a later time."""
    pass

    def __init__(self, irc):
        self.__parent = super(Remind, self)
        self.__parent.__init__(irc)
        self.events = {}

    def _isNumber(self, s):
        """Determines if something is a number."""
        try:
            int(s)
            return True
        except ValueError:
            return False

    def _getMultiplier(self, s):
        """Determines the number of seconds in a certain time unit."""
        s = s.lower()
        if s == 's' or s == 'sec' or s == 'secs' or s == 'second' or s == 'seconds':
            return 1 # second = 1 second
        elif s == 'm' or s == 'min' or s == 'mins' or s == 'minute' or s == 'minutes':
            return 60 # seconds = 1 minute
        elif s == 'h' or s == 'hr' or s == 'hrs' or s == 'hour' or s == 'hours':
            return 3600 # seconds = 1 hour
        elif s == 'd' or s == 'day' or s == 'days':
            return 86400 # seconds = 1 day
        elif s == 'w' or s == 'wk' or s == 'wks' or s == 'week' or s == 'weeks':
            return 604800 # seconds = 1 week
        elif s == 'f' or s == 'fn' or s == 'fns' or s == 'fortnight' or s == 'fortnights':
            return 1209600 # seconds = 1 fortnight
        elif s == 'mo' or s == 'mos' or s == 'month' or s == 'months':
            return 2592000 # seconds = 30 days
        elif s == 'y' or s == 'yr' or s == 'yrs' or s == 'year' or s == 'years':
            return 31536000 # seconds = 365 days
        else:
            return 0 # invalid

    def _makeRemindFunction(self, irc, msg, name, what):
        """Makes a function suitable for scheduling a reminder."""
        def f():
            del self.events[str(f.eventId)]
            irc.reply(name + ': ' + what, prefixNick=False)
        return f

    def remind(self, irc, msg, args, a):
        """[me|<who>] [in] <time> [of|to] <what>
        
        Reminds people of something in a set time.
        <who> must be an IRC nickname; default is yourself.
        <time> must be a string describing time, such as 2 hr 30 min 15 s.
        <what> is what to be reminded of.
        """
        tname = irc.msg.nick
        ttime = 0
        twhat = 'reminder!'
        # begin parsing
        i = 0
        if i < len(a) and not (a[i] == 'in' or a[i] == 'of' or a[i] == 'to' or self._isNumber(a[i])):
            if a[i] != 'me':
                tname = a[i]
            i += 1
        if i < len(a) and a[i] == 'in':
            i += 1
        while i < len(a) and self._isNumber(a[i]):
            v = int(a[i])
            i += 1
            m = 60
            if i < len(a):
                m = self._getMultiplier(a[i])
                if m > 0:
                    i += 1
                else:
                    m = 60
            ttime += v * m
        if i < len(a) and (a[i] == 'of' or a[i] == 'to'):
            i += 1
        if i < len(a):
            twhat = ' '.join(a[i:len(a)])
        # end parsing
        f = self._makeRemindFunction(irc, msg, tname, twhat)
        id = schedule.addEvent(f, time.time() + ttime)
        f.eventId = id
        self.events[str(id)] = tname + ': ' + twhat
        irc.reply('Okay, will remind in ' + utils.timeElapsed(ttime) + ' (id: ' + str(id) + ')')
    remind = wrap(remind, [many('something')])

    def remove(self, irc, msg, args, id):
        """<id>

        Removes the reminder scheduled with id <id> from the schedule.
        """
        if id in self.events:
            del self.events[id]
            try:
                id = int(id)
            except ValueError:
                pass
            try:
                schedule.removeEvent(id)
                irc.replySuccess()
            except KeyError:
                irc.error('Invalid event id.')
        else:
            irc.error('Invalid event id.')
    remove = wrap(remove, ['lowered'])

    def list(self, irc, msg, args):
        """takes no arguments

        Lists the currently scheduled reminders.
        """
        L = self.events.items()
        if L:
            L.sort()
            for (i, (name, command)) in enumerate(L):
                L[i] = format('%s: %q', name, command)
            irc.reply(format('%L', L))
        else:
            irc.reply('There are currently no scheduled reminders.')
    list = wrap(list)

Class = Remind

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
