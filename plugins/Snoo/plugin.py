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

import re

import supybot.conf as conf
import supybot.utils as utils
import supybot.ircdb as ircdb
import supybot.world as world
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

from requests.exceptions import HTTPError
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
        if isinstance(name1, str) and name1.startswith('r/'):
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

class RedditorDB(plugins.ChannelUserDB):
    def serialize(self, v):
        return [v]

    def deserialize(self, channel, id, L):
        if len(L) != 1:
            raise ValueError
        return L[0]

redditors_filename = conf.supybot.directories.data.dirize('Redditors.db')

# fixme: make configurable
ignore_r_snarf = []

import supybot.utils as utils
def subs2links(subs):
    urls = []
    for sub in subs:
        tryurl = 'http://reddit.com/' + sub
        try:
            fp = utils.web.getUrlFd(tryurl)
        except utils.web.Error:
            continue
        if '/search?q=' not in fp.geturl():
            urls.append(tryurl)
        continue
    return ' '.join(['< %s >' % url for url in urls])


class Snoo(callbacks.Plugin):
    """Interact with reddit"""
    threaded = True


    def __init__(self, irc):
        self.__parent = super(Snoo, self)
        self.__parent.__init__(irc)
        self.subcache = {}
        self.db = RedditorDB(redditors_filename)
        world.flushers.append(self.db.flush)
        return

    def die(self):
        if self.db.flush in world.flushers:
            world.flushers.remove(self.db.flush)
        self.db.close()
        self.__parent.die()

    def doPrivmsg(self, irc, msg):
        if not self.registryValue('rSlashLinks'):
            return

        ignored_subs = self.registryValue('rIgnoredSubs')
        rslmap = dict()
        for pair in self.registryValue('rSlashLinkMap'):
            k,v = pair.split(':')
            rslmap[k.lower()] = v

        subs = []

        for word in msg.args[1].split():
            if not word: 
                continue
            parts = word.split('r/')
            if len(parts) != 2: 
                continue
            if parts[0] not in ['','/']:
                continue
            sub = parts[1]
            if sub in ignore_r_snarf:
                continue
            sub = rslmap.get(sub.lower(),sub)
            subs.append('r/' + sub)

        # cut-and-paste programmers suck

        for word in msg.args[1].split():
            if not word: 
                continue
            parts = word.split('u/')
            if len(parts) != 2: 
                continue
            if parts[0] not in ['','/']:
                continue
            sub = parts[1]
            if sub in ignore_r_snarf:
                continue
            sub = rslmap.get(sub.lower(),sub)
            subs.append('u/' + sub)

        if not subs:
            return

        sublinks = subs2links(subs)
        if not sublinks:
            #irc.reply('No real reddit links', prefixNick=False)
            return
        irc.reply('Reddit links: %s' % sublinks, prefixNick=False)
        return

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
            cid = sub.id    # trigger error if sub d.n.e.
        except ValueError:
            if irc:
                irc.reply('r/%s does not appear to exist' % name)
            return
        except HTTPError:
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

        lst = meth(limit=1)
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

        msg = '%s in r/%s %s: "%s" by %s%s < http://redd.it/%s >' % \
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


    def _get_redname(self, channel, user_or_nick):
        '''
        Return the redditor name that is associated to the user_or_nick.
        '''
        fallback = user_or_nick
        uid = user_or_nick
        if isinstance(user_or_nick, ircdb.IrcUser):
            fallback = user_or_nick.name
            uid = user_or_nick.id
        self.log.debug('Snoo._get_redname: UID=%s' % uid)
        try:
            name = self.db[channel, uid]
        except KeyError:
            return fallback
        return name or fallback

    def redditor(self, irc, msg, args, channel, user, name):
        '''[<channel>] RedditName
        
        Associate your reddit name with your IRC identity (use name
        "delete" to disassociation).  This will associate to your
        current nick or your bot ID if you are registered with the
        bot (see help register).'''
        uid = msg.nick
        if user:
            uid = user.id
        
        if name.lower() in ['', 'none','rm','remove','delete']:
            try:
                self.db[channel, uid] = ''
            except KeyError:
                pass
            irc.reply('You are not associated with any redditor.')
            return
        self.db[channel, uid] = name
            
        irc.reply('I associate you with redditor "%s" in %s (using: id %s)' %\
                      (name, channel, uid))
        return
    redditor = wrap(redditor, ['channel', optional('user'), 'something'])

    def whoami(self, irc, msg, args, channel, user):
        '''[<channel>]
        
        Show your the reddit name associated with your bot user or nick.
        '''
        name = self._get_redname(channel, user or msg.nick)
        irc.reply('I think you are redditor "%s" in %s' % (name, channel))
        return
    whoami = wrap(whoami, ['channel', optional('user')])

    def whois(self, irc, msg, args, channel, user_or_nick):
        '''[<channel>] <user|nick>
        See who the redditor is
        '''
        name = self._get_redname(channel, user_or_nick)
        irc.reply('I think it is redditor "%s" in %s' % (name, channel))
        return
    whois = wrap(whois, ['channel', first('otherUser','nick')])

    def _get_flair_text(self, redname, sub):
        f = sub.get_flair(redname)
        if not f:
            return
        if not f['flair_text']:
            return
        if f['user'] != redname:
            return
        return f['flair_text']

    def _reply_with_flair(self, irc, name, flair, sub):
        irc.reply('%s has %s with %s' % (name, flair, sub),
                  prefixNick=False)
        return

    def _real_flair(self, irc, msg, args, channel, thing1, thing2):
        """[<chanel>] [<name> and/or r/<subreddit>]

        Show some flair.
        """
        defnick = msg.nick
        defsub = self.registryValue('subreddit')        
        name, subname = awkwardly_pick_rs(thing1,thing2, defnick, defsub)
        redname = self._get_redname(channel, name)

        sub = self.get_sub(subname, irc)
        if not sub: return 

        ft = self._get_flair_text(redname, sub)
        if ft:
            self._reply_with_flair(irc, redname, ft, sub.display_name)
            return

        irc.reply('%s has no flair in %s or has a different reddit name and that is okay.' % (redname,sub.display_name))
        return
    flair = wrap(_real_flair, ['channel', optional(first('otherUser','something')), optional('something')])

    def coin(self, irc, msg, args, channel, name):
        """[<channel>] [<user|nick>]"

        Show your or another's flair from the default subreddit.  See
        the flair command for a more general command.
        """
        subname = self.registryValue('subreddit')
        self._real_flair(irc, msg, args, channel, name, subname)
        return
    coin = wrap(coin, ['channel', optional(first('otherUser','something'))] )

    def poem(self, irc, msg, args, channel, name, nwords, nskip):
        """<name> [<nwords> [<nskip>]]

        Generate a poem based on recent reddit comments by <name>.
        Optionally specify how many <nwords> to generate and how many
        words to <nskip> in the corpus.
        """
        redname = self._get_redname(channel, name or msg.nick)
        try:
            red = reddit.get_redditor(redname)
        except HTTPError:
            red = None
        
        if not red:
            irc.reply('I can not find any redditor by that name')
            return

        msg = poetry(red, nwords, nskip)
        irc.reply('<%s> %s' % (redname, msg), prefixNick=False)
        return

    poem = wrap(poem, ['channel',
                       optional(first('otherUser','something')),
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

    def fip(self, irc, msg, args, channel, name):
        '''[<name>]

        Print the fake Internet points that <name> has garnered on reddit.'''
        redname = self._get_redname(channel, name or msg.nick)
        try:
            red = reddit.get_redditor(redname)
        except HTTPError:
            red = None

        if not red:
            irc.reply('I can not find any redditor by that name')
            return

        irc.reply('fake Internet points for %s: %d (links) / %d (comments)' % \
                      (redname, red.link_karma, red.comment_karma))

        return
    fip = wrap(fip, ['channel', optional(first('otherUser','something'))])
        
Class = Snoo


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
