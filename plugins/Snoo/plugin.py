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
import supybot.ircdb as ircdb
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks


import praw
myurl = 'https://github.com/frumiousbandersnatch/sobrieti-plugins'
reddit = praw.Reddit('sobrieti IRC bot for r/stopdrinking. %s' % myurl)

def awkwardly_pick_rs(name1, name2, defred, defsub):
    """
    Return (redditor,subreddit)
    """

    if name1 and name2:
        if name2.startswith('r/'):
            name2 = name2[2:]
        return (name1,name2)

    if name1:
        if name1.startswith('r/'):
            name1 = name1[2:]
            return (defred, name1)
        return (name1, defsub)

    return (defred, defsub)


class Snoo(callbacks.Plugin):
    """Interact with reddit"""
    threaded = True


    def flair(self, irc, msg, args, name1, name2):
        """[<redditor> and/or r/<subreddit>]

        Show some flair.
        """
        defnick = msg.nick 
        defsub = self.registryValue('subreddit')

        red, sub = awkwardly_pick_rs(name1,name2, defnick, defsub)

        print 'red="%s", sub="%s", name1=%s, name2=%s, nick=%s, sub=%s' %\
            (red,sub,name1,name2,defnick,defsub)

        subreddit = reddit.get_subreddit(sub)
        f = subreddit.get_flair(red)

        if f['flair_text']:
            irc.reply('%s has %s with %s' % (red, f['flair_text'], sub),
                      prefixNick=False)
            return

        # try again with an association

        user = ircdb.users.getUser(msg.nick)
        print 'USER: "%s"' % user
        print '\tASSOCIATIONS: "%s"' % str(user.associations)
        for assoc in user.associations:
            print '\tASSOC: "%s"' % assoc
            try:
                name, domain = assoc.split('|')
            except ValueError:
                continue
            if domain != 'reddit':
                continue
            f = subreddit.get_flair(name)
            if not f['flair_text']:
                continue

            irc.reply('%s (as %s) has %s with %s' % \
                          (red, name, f['flair_text'], sub),
                      prefixNick=False)
            return
        irc.reply('%s has no flair in %s and that is okay.' % (red,sub))
        return
    flair = wrap(flair, [optional('something'), optional('something')])

Class = Snoo


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
