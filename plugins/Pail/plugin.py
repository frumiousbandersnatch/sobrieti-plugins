###
# Copyright (c) 2013, Frumious Bandersnatch
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

import supybot.conf as conf
import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('Pail')
except:
    # Placeholder that allows to run the plugin on a bot
    # without the i18n module
    _ = lambda x:x


import shelve
import bag
reload(bag)                     # support reloading this module

class Pail(callbacks.Plugin):
    """Add the help for "@plugin help Pail" here
    This should describe *how* to use this plugin."""
    threaded = True

    def __init__(self, irc):
        super(Pail, self).__init__(irc)
        self.filename = conf.supybot.directories.data.dirize('pail.db')
        self._reload()

    def _reload(self):
        self.db = shelve.open(self.filename, writeback=True)
        self.bag = bag.Bag(store=self.db)

    def reloaddb(self, irc, msg, args):
        '''reload Pail database'''
        self._reload()
        irc.reply('Reloaded Pail DB')
        return
    reloaddb = wrap(reloaddb)

    def add(self, irc, msg, args, name, value):
        '''<name> <value>

        Add thing with <name> and <value> to the pail.'''
        self.bag.add(name,value)
        irc.reply('I now know %d things about "%s", just added "%s"' % \
                  (len(self.bag.get_all(name)), name, value))
        return
    add = wrap(add, ['something', 'text'])
        
    def get(self, irc, msg, args, name):
        '''<name>

        Get something by <name> from the pail.
        '''
        p = self.bag[name]
        irc.reply('%s'%p, prefixNick=False)
        return
    get = wrap(get, ['something'])

    def dump(self, irc, msg, args, name):
        '''Dump the Pail db'''
        keys = self.bag.keys()
        irc.reply('I hold %d things: %s' % \
                  (len(keys), ', '.join(keys)), prefixNick=False)
        if name:
            irc.reply('%s: %s' % (name, ', '.join(self.bag.get_all(name))),
                      prefixNick=False)
        return
    dump = wrap(dump, [optional('something')])

Class = Pail


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
