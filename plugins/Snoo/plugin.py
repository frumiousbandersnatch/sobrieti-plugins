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


rank_types = ['hot','new','top','controversial']
rank_terms = ['week','month','year']

class Snoo(callbacks.Plugin):
    """Interact with reddit"""
    threaded = True


    def __init__(self, irc):
        self.__parent = super(Snoo, self)
        self.__parent.__init__(irc)
        self.subcache = {}

    def get_sub(self, name, irc = None):
        if not name:
            name = self.registryValue('subreddit')
        if name.startswith('r/'):
            name = name[2:]
        if not name:
            return

        sub = self.subcache.get(name)
        if not sub:
            sub = reddit.get_subreddit(name)
        if not sub:
            return 

        try:
            cid = sub.content_id    # trigger error
        except ValueError:
            if irc:
                irc.reply('r/%s does not appear to exist' % name)
            return
        except praw.HTTPError:
            if irc:
                irc.reply('failed to load r/%s' % name)
            return

        self.subcache[name] = sub
        return sub

    def rank(self, irc, msg, args, type, term, name):
        """[<subreddit> [<type>] [<term>]]]

        Show the ranking post of the <subreddit> of rank <type> over
        given time <term>.
        """
        if not type:
            type = 'top'
        if term and type not in ['hot','new']:
            _term_ = '_from_' + term
            rankstr = '%s (%s)' % (type,term)
        else:
            _term_ = ''
            rankstr = type

        sub = self.get_sub(name, irc)
        if not sub: return

        methname = 'sub.get_%s%s' % (type,_term_)
        meth = eval(methname)

        lst = meth(1)
        try:
            lst = [x for x in lst]
        except ValueError,err:
            irc.reply("reddit barfed, sorry")
            return

        if not len(lst):
            irc.reply('Weird, no %s entries' % type)
            return
        
        first = lst[0]
        
        flair = ''
        if first.author_flair_text:
            flair = ' (%s)' % first.author_flair_text

        score = '(+%d/-%d)' % (first.ups, first.downs)

        msg = '%s in r/%s %s: "%s" by %s%s <http://redd.it/%s>' % \
            (rankstr.capitalize(), sub.display_name, score,
             first.title, first.author, flair, first.id)
        irc.reply(msg, prefixNick=False)
        return

    rank = wrap(rank, [
            optional(('literal',rank_types)),
            optional(('literal',rank_terms)),
            optional('something'), 
            ])

    def subscribers(self, irc, msg, args, name):
        """[<subreddit>]

        Show the number of subcribers to the given subreddit.
        """
        sub = self.get_sub(name, irc)
        if not sub: return

        ns = sub.subscribers
        aa = sub.accounts_active
        irc.reply('%s has %d subscribers of which %d recently visited' % \
                      (sub.display_name, ns, aa),
                  prefixNick=False)
        return
    subscribers = wrap(subscribers, [optional("something")])
    stats = subscribers

    def flair(self, irc, msg, args, name1, name2):
        """[<redditor> and/or r/<subreddit>]

        Show some flair.
        """
        defnick = msg.nick 
        defsub = self.registryValue('subreddit')

        red, subname = awkwardly_pick_rs(name1,name2, defnick, defsub)

        sub = self.get_sub(subname, irc)
        if not sub: return 

        f = sub.get_flair(red)

        if f['flair_text']:
            irc.reply('%s has %s with %s' % \
                          (red, f['flair_text'], sub.display_name),
                      prefixNick=False)
            return

        # try again with an association

        user = ircdb.users.getUser(msg.nick)
        for assoc in user.associations:
            try:
                name, domain = assoc.split('|')
            except ValueError:
                continue
            if domain != 'reddit':
                continue
            f = sub.get_flair(name)
            if not f['flair_text']:
                continue

            irc.reply('%s (as %s) has %s with %s' % \
                          (red, name, f['flair_text'], sub.display_name),
                      prefixNick=False)
            return
        irc.reply('%s has no flair in %s and that is okay.' % \
                      (red,sub.display_name))
        return
    flair = wrap(flair, [optional('something'), optional('something')])

Class = Snoo


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
