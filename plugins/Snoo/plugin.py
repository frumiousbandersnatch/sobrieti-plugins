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


import collections, random

def generate_poem(red, ngrams, nwords, nskip):
    prev = None
    ret = []
    while nwords:
        words = ngrams[prev][1:]
        #print 'ngrams["%s"] = "%s"' % (prev, words)
        if not words:
            return 'ERROR, something is wrong, no words from %s' % red.name
        prev = random.choice(words)
        if not prev: 
            return 'ERROR, no poem for you (%s)' % str(words)
        if nskip:
            nskip -= 1
            continue
        ret.append(prev)
        nwords -= 1
        continue
    poem = ' '.join(ret)
    return poem

def poetry(red, nwords, nskip):
    '''
    Generate poetry form the user's recent comments
    '''

    corpus = []
    try:
        overview = [o for o in red.get_overview()]
    except KeyError:
        return 'ERROR, failed to get overview for "%s"' % red.name

    for o in overview:
        line = str(o).strip()
        for word in line.split():
            word = word.strip()
            if word.endswith('...'): 
                continue # some shortening by praw?
            if word.startswith('&') and word.endswith(';'):
                continue # skip HTML entities that can creep in
            if word.startswith('[') and word.endswith(']'):
                continue
            if word.startswith('(') and word.endswith(')'):
                continue
            if word.startswith('[') and word.endswith(')'):
                continue        # markdown links
            if word.startswith('(') and word.endswith(']'):
                continue        # markdown typo links
            if word.startswith('"') or word.endswith('"'):
                word = word.replace('"','')
            if word.startswith("'") or word.endswith("'"):
                word = word.replace("'",'')
            if word.endswith('.'):
                word = word.replace('.','')


            word = word.lower()
            word = word.replace(',','')
            word = word.replace('.','')
            if word.startswith("http:"): continue
            if word.startswith("https:"): continue
            if not word: continue
            corpus.append(word)
            #print 'add to corpus: "%s"' % word
            continue
        continue
    
    ngrams = collections.defaultdict(lambda: [None])
    prev = None
    for word in corpus:
        ngrams[prev].append(word)
        #print 'prev="%s", word="%s"' % (prev,word)
        prev = word
        continue

    #print 'got corpus of size %d' % len(ngrams)
    return generate_poem(red, ngrams, nwords, nskip)

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


    def get_assoc_redditors(self, nick):
        """Try to return the redditors associated with the nick."""

        try:
            user = ircdb.users.getUser(nick)
        except KeyError:
            return []

        if not user:
            if irc:
                irc.reply('No associated redditor with: "%s"' % nick)
            return []

        ret = []
        for assoc in user.associations:
            try:
                name, domain = assoc.split('|')
            except ValueError:
                continue
            if domain != 'reddit':
                continue
            ret.append(name)
        return ret
        
    def _real_flair(self, irc, msg, args, name1, name2):
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
        for name in self.get_assoc_redditors(red):
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
    flair = wrap(_real_flair, [optional('something'), optional('something')])

    def coin(self, irc, msg, args, name):
        """[<name>]"

        Show your or another's flair from the default subreddit.  See
        the flair command for a more general command.
        """
        if not name:
            name = msg.nick
        subname = self.registryValue('subreddit')
        self._real_flair(irc, msg, args, name, subname)
        return
    coin = wrap(coin, [optional("something")])

    def get_redditor(self, name):
        """Try to return reddtor object."""
        maybe = [name]
        assoc = self.get_assoc_redditors(name)
        if assoc:
            maybe = assoc

        for name in maybe:
            try:
                red = reddit.get_redditor(name)
            except praw.HTTPError:
                continue
            else:
                return red
        return 

    def poem(self, irc, msg, args, name, nwords, nskip):
        """<name> [<nwords> [<nskip>]]

        Generate a poem based on recent reddit comments by <name>.
        Optionally specify how many <nwords> to generate and how many
        words to <nskip> in the corpus.
        """
        if not name:
            name = msg.nick
        red = self.get_redditor(name)
        if not red:
            irc.reply('failed to find "%s" on reddit' % name)
            return

        msg = poetry(red, nwords, nskip)
        irc.reply('<%s> %s' % (name, msg), prefixNick=False)
        return

    poem = wrap(poem, ['something',
                       optional('int',10),
                       optional('int',5)])

    def mods(self, irc, msg, args, subname):
        '''[<subreddit>]

        Print the mods for the given or defalt sub-reddit'''
    
        if not subname:
            subname = self.registryValue('subreddit')
        sub = self.get_sub(subname, irc)
        if not sub: return

        moditr = sub.get_moderators()
        names = ', '.join([m.name for m in moditr])
        irc.reply('mods for r/%s are: %s' % (subname, names))

        return
    mods = wrap(mods, [optional('something')])

    def fip(self, irc, msg, args, name):
        '''[<name>]

        Print the fake Internet points that <name> has garnered on reddit.'''

        if not name:
            name = msg.nick
        red = self.get_redditor(name)
        pname = name
        if name != red.name:
            pname = '%s (as %s)' % (name, red.name)
        if not red:
            irc.reply('failed to find %s on reddit' % pname)
            return

        irc.reply('fake Internet points for %s: %d (links) and %d (comments)' % \
                      (pname, red.link_karma, red.comment_karma))
        return
    fip = wrap(fip, [optional('something')])
        
Class = Snoo


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
