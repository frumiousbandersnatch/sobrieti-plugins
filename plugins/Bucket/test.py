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

from supybot.test import *

class BucketTestCase(ChannelPluginTestCase):
    plugins = ('Bucket',)

    def testSay(self):
        self.assertResponse('say hi', 'Hi!', to="#test", usePrefixChar=False)

    def testFactoid(self):
        self.feedMsg('cats are smart', to=self.irc.nick)
        self.assertRegexp(' ', '.*(cats|Okay).*', to=self.channel)
        self.feedMsg('cats', to=self.irc.nick)        
        self.assertResponse(' ', 'cats are smart', to=self.channel, usePrefixChar=False)

    def testLiteral(self):
        self.assertRegex('literal cats', '.*cats.*')

    def testItems(self):
        self.assertRegexp('inventory', '.*')
        m = ircmsgs.action(self.channel, f'gives {self.irc.nick} a brown cat')
        self.irc.feedMsg(m)
        self.assertRegexp(' ', '.*', to=self.channel)
        self.assertRegexp('inventory', '.*a brown cat.*')
        self.assertRegexp('give an orange cat', '.*', to=self.channel)



# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:
