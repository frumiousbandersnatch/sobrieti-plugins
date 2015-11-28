###
# Copyright (c) 2015, Frumious Bandersnatch
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
import supybot.ircmsgs as ircmsgs
import supybot.callbacks as callbacks
try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('TIA')
except ImportError:
    # Placeholder that allows to run the plugin on a bot
    # without the i18n module
    _ = lambda x:x


import time
import datetime
import irctia.models
import irctia.session

tiadb_filename = conf.supybot.directories.data.dirize('TIA.db')

class TIA(callbacks.Plugin):
    'Total Information Awareness'

    def __init__(self, irc):
        self.__parent = super(TIA, self)
        self.__parent.__init__(irc)
        self.subcache = {}
        self.ses = irctia.session.get(tiadb_filename, echo = False)

    def _add(self, irc, msg, kind):
        #obj = Nick(kind=kind, channel=msg.args[0], nick=msg.nick, user=msg.user, host=msg.host)
        channel = ''
        if kind == 'nick':
            newnick = msg.args[0]
            oldnick = msg.nick
        if kind in ['quit','part','kick']:
            channel = msg.args[0]
            newnick = None
            oldnick = msg.nick
        if kind in ['join']:
            channel = msg.args[0]
            newnick = msg.nick
            oldnick = None

        stamp = datetime.datetime(*time.gmtime()[:6])
        obj = irctia.models.Nick(kind = kind, channel = channel, new = newnick, old = oldnick,
                                 user = msg.user, host = msg.host, stamp=stamp)
        self.ses.add(obj)
        self.ses.commit()
        # print 'TIA:',kind
        # print 'MSG args:',msg.args
        # print 'MSG obj:',msg
        # print msg.nick,msg.user,getattr(msg,'host','NOHOST'),msg.prefix
        # print 'IRC obj:',irc
        # print irc.nick,irc.user,getattr(irc,'host','NOHOST'),irc.prefix

    def doJoin(self, irc, msg):
        self._add(irc, msg, 'join')
        nick = msg.nick
        irc.queueMsg(ircmsgs.whois(nick, nick))

    def doPart(self, irc, msg):
        self._add(irc, msg, 'part')
    def doKick(self, irc, msg):
        self._add(irc, msg, 'kick')
    def doNick(self, irc, msg):
        self._add(irc, msg, 'nick')

    ### turn off until I add capabilities.
    # def joins(self, irc, msg, args, channel, query):
    #     '''[channel] query

    #     query past joins in <channel>.  By default, query is
    #     interpreted as a fragment of a "hostname".  A query may be
    #     made specific to a nick, user or host by prepending it with
    #     "nick:", etc.'''

    #     Nick = irctia.models.Nick
    #     things = dict(nick=Nick.new, user=Nick.user, host=Nick.host)

    #     q = self.ses.query(Nick).filter(Nick.kind == 'join')

    #     for chunk in query.split():
    #         if ':' in chunk:
    #             which, what = chunk.split(':',1)
    #             thing = things.get(which.lower(), None)
    #             if thing is None:
    #                 continue
    #             if '%' in what:
    #                 q = q.filter(thing.like(what))
    #             else:
    #                 q = q.filter(thing == what)
    #             continue
    #         q = q.filter(Nick.host.like('%'+chunk+'%'))
    #     found = list()
    #     for obj in q.order_by(Nick.stamp.desc()).all():
    #         if obj.mask in found:
    #             continue
    #         found.append(obj.mask)
    #     if not found:
    #         irc.reply('No joins for "%s"' % query)
    #         return
    #     fstr = ' '.join(found)
    #     irc.reply(fstr)
    #     return
    # joins = wrap(joins, ['channel', 'admin', 'something'])


    # def whois(self, irc, msg, args, nick):
    #     '''nick

    #     run /whois query on nick'''
    #     irc.reply("whoising %s" % nick)
    #     irc.queueMsg(ircmsgs.whois(nick, nick))
    #     return
    # whois = wrap(whois, ['nick'])

    # msg args: ('sobrieti', 'frumious', '#sdcabal #cabal @#stopdrinking')
    # msg.command: 319
    def do319(self, irc, msg):
        """/whois"""

        print 'msg:',msg
        print 'msg.args:',msg.args

        stamp = datetime.datetime(*time.gmtime()[:6])
        nick = msg.args[1]
        chanlist = msg.args[2]
        obj = irctia.models.Chanlist(nick = nick, chanlist=chanlist, stamp=stamp)
        self.ses.add(obj)
        self.ses.commit()
        return

    pass



Class = TIA


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

# do311: irc=<supybot.callbacks.ReplyIrcProxy object at 0xb3ab370c>  msg=:sobrieti.bot.nu 311 sobrieti frumious frumious sd-79l.gjc.ealr8h.IP * :frumious

# msg args: ('sobrieti', 'frumious', 'frumious', 'sd-79l.gjc.ealr8h.IP', '*', 'frumious')
# msg.command: 311

# irc dict: {'msg': IrcMsg(prefix="sobrieti.bot.nu", command="311", args=('sobrieti', 'frumious', 'frumious', 'sd-79l.gjc.ealr8h.IP', '*', 'frumious')), 'irc': <irclib.Irc object for sdnet>}
# do311: irc=<supybot.callbacks.ReplyIrcProxy object at 0xb2f5c14c>  msg=:sobrieti.bot.nu 319 sobrieti frumious :#sdcabal #cabal @#stopdrinking

# msg args: ('sobrieti', 'frumious', '#sdcabal #cabal @#stopdrinking')
# msg.command: 319

# irc dict: {'msg': IrcMsg(prefix="sobrieti.bot.nu", command="319", args=('sobrieti', 'frumious', '#sdcabal #cabal @#stopdrinking')), 'irc': <irclib.Irc object for sdnet>}
# do311: irc=<supybot.callbacks.ReplyIrcProxy object at 0xb2f9668c>  msg=:sobrieti.bot.nu 312 sobrieti frumious sobrieti.bot.nu :SobrietIRC

# msg args: ('sobrieti', 'frumious', 'sobrieti.bot.nu', 'SobrietIRC')
# msg.command: 312

# irc dict: {'msg': IrcMsg(prefix="sobrieti.bot.nu", command="312", args=('sobrieti', 'frumious', 'sobrieti.bot.nu', 'SobrietIRC')), 'irc': <irclib.Irc object for sdnet>}
# do311: irc=<supybot.callbacks.ReplyIrcProxy object at 0xb2f5c9cc>  msg=:sobrieti.bot.nu 317 sobrieti frumious 0 1445792393 :seconds idle, signon time

# msg args: ('sobrieti', 'frumious', '0', '1445792393', 'seconds idle, signon time')
# msg.command: 317

# irc dict: {'msg': IrcMsg(prefix="sobrieti.bot.nu", command="317", args=('sobrieti', 'frumious', '0', '1445792393', 'seconds idle, signon time')), 'irc': <irclib.Irc object for sdnet>}


#         311     RPL_WHOISUSER
#                         "<nick> <user> <host> * :<real name>"
#         312     RPL_WHOISSERVER
#                         "<nick> <server> :<server info>"
#         313     RPL_WHOISOPERATOR
#                         "<nick> :is an IRC operator"
#         317     RPL_WHOISIDLE
#                         "<nick> <integer> :seconds idle"
#         318     RPL_ENDOFWHOIS
#                         "<nick> :End of /WHOIS list"
#         319     RPL_WHOISCHANNELS
#                         "<nick> :{[@|+]<channel><space>}"

#                 - Replies 311 - 313, 317 - 319 are all replies
#                   generated in response to a WHOIS message.  Given that
#                   there are enough parameters present, the answering
#                   server must either formulate a reply out of the above
#                   numerics (if the query nick is found) or return an
#                   error reply.  The '*' in RPL_WHOISUSER is there as
#                   the literal character and not as a wild card.  For
#                   each reply set, only RPL_WHOISCHANNELS may appear
#                   more than once (for long lists of channel names).
#                   The '@' and '+' characters next to the channel name
#                   indicate whether a client is a channel operator or
#                   has been granted permission to speak on a moderated
#                   channel.  The RPL_ENDOFWHOIS reply is used to mark
#                   the end of processing a WHOIS message.
