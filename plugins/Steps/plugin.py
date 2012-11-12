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

import steps
reload(steps)

def get_flavor_mod(flavor):
    if flavor in steps.__all__:
        return steps.__dict__[flavor]

    for modname in steps.__all__:
        mod = steps.__dict__[modname]
        for maybe in [modname, mod.name] + mod.abbrevs:
            if maybe.lower() == flavor.lower():
                return mod
    return None


def get_all_flavor():
    ret = set()
    for modname in steps.__all__:
        mod = steps.__dict__[modname]
        for name in [modname, mod.name] + mod.abbrevs:
            ret.add(name)
            ret.add(name.upper())
            ret.add(name.lower())
            ret.add(name.capitalize())
    ret = list(ret)
    ret.sort()
    return tuple(ret)

class Steps(callbacks.Plugin):
    """Print a select or random step of a particular flavor."""

    def list(self, irc, msg, args):
        flavors = []
        for modname in steps.__all__:
            mod = steps.__dict__[modname]
            flavors.append('%s[%d]'% (mod.name, len(mod.steps)))
        flavors.sort()
        flavors = ', '.join(flavors)
        irc.reply('available steps: %s' % flavors)

    def step(self, irc, msg, args, number1, flavor, number2):
        """[<flavor> and/or <number>]"""
        number = number1 or number2

        if not flavor:
            flavor = random.choice(steps.__all__)
        fmod = get_flavor_mod(flavor)

        maxn = len(fmod.steps)
        if not number: 
            number = random.randint(1,maxn)

        if number < 1: maxn = 1
        if number > maxn: number = maxn
        
        index = number-1

        res = '%s step %d/%d: %s' % \
            (fmod.name, number, maxn, fmod.steps[index])
        irc.reply(res)
    
    step = wrap(step, [
            optional('int'),
            optional(('literal', get_all_flavor())),
            optional('int'),
            ])
    steps = step

    pass


Class = Steps


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
