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


import random

class Dice(callbacks.Plugin):
    """Roll dice and display the results."""

    dice_str = [unichr(9856+ind) for ind in range(6)]

    def dice(self, irc, msg, args, number):
        """[<number>]

        Roll <number> of six sided dice.
        """
        die = []
        tot = 0
        for ind in range(number):
            r = random.randint(1,6)
            tot += r
            die.append(Dice.dice_str[r-1])
        rolls = ' '.join(die)
        resp = '%s = %d' % (rolls, tot)
        resp = resp.encode('utf8','ignore')
        irc.reply(resp)
    dice = wrap(dice, [optional('int',2)])

    def ask(self, irc, msg, args, stuff):
        """Ask a yes or no question or a 'this or that or the other'"""
        if 'or' in stuff:
            stuff = ' '.join(stuff).split(' or ')
            res = random.choice(stuff).strip().encode('utf-8')
        else:
            res = random.choice(['yes', 'no'])

        irc.reply(res)
    ask = wrap(ask, [many('something')])

    def rand(self, irc, msg, args, num1, num2):
        numbers = []
        if num1 is not None:
            numbers.append(num1)
        if num2 is not None:
            numbers.append(num2)            
        a = min(numbers)
        b = max(numbers)

        r = random.randint(a,b)
        irc.reply('%d' % r)
        return
    rand = wrap(rand, ['int', optional('int',None)])

    pass


Class = Dice


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
