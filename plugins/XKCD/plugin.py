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

import os
from supybot import utils, plugins, ircutils, callbacks
import supybot.ircmsgs as ircmsgs
import supybot.dbi as dbi
from supybot.commands import *
try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('XKCD')
except ImportError:
    # Placeholder that allows to run the plugin on a bot
    # without the i18n module
    _ = lambda x: x

import re
import json
import sqlite3

xkcd_base_url = 'https://xkcd.com'
xkcd_url_id_re = re.compile(f"{xkcd_base_url}/([0-9]+)[/]?$")

def xkcd_comic_url(num):
    if num is None:
        return xkcd_base_url
    return f'{xkcd_base_url}/{num}'

def xkcd_api_url(num):
    return xkcd_comic_url(num) + '/info.0.json'

xkcd_fields = [
        ('num',int),
        ('day',int),
        ('month',int),
        ('year',int),
        ('title',str),
        ('safe_title',str),     # ?
        ('alt',str),
        ('transcript',str),
        ('img',str),          # img url
        ('link',str),         # ?
        ('news',str),         # ?
]

xkcd_field_names = [f[0] for f in xkcd_fields]

def xkcd_typify(**fields):
    tf = {n:f for n,f in xkcd_fields}
    return {k:tf[k](v) for k,v in fields.items()}

def xkcd_arr_to_dict(field_list):
    #print(field_list)
    return {f[0]:f[1](a) for f,a in zip(xkcd_fields, field_list)}


class XkcdRecord(dbi.Record):
    # reflect the info.0.json schema
    __fields__ = xkcd_fields

    @property
    def aslist(self):
        return [getattr(self, c) for c in xkcd_field_names]

    @property
    def asdict(self):
        return {c:getattr(self, c) for c in xkcd_field_names}

    @property
    def url(self):
        return xkcd_comic_url(self.num)

    @property
    def date(self):
        return f'{self.year}-{self.month:02d}-{self.day:02d}'

    def __str__(self):
        return f'{self.title} {self.url} ({self.date})'

def xkcd_get(num=None):
    api = xkcd_api_url(num)
    try:
        jtext = utils.web.getUrlContent(api)
    except utils.web.Error as err:
        raise ValueError(f'no xkcd #{num}')
    info = json.loads(jtext)
    #print(f'got xkcd json: {info}')
    info = xkcd_typify(**info)
    return  XkcdRecord(**info) # xkcd.com can crash us by extending return values! :)


# see plugins.QuoteGrabs.plugin for example
class SqliteXkcdDB(object):

    def __init__(self, filename):
        self.dbs = ircutils.IrcDict()
        self.filename = filename

    def close(self):
        for db in self.dbs.values():
            db.close()

    # We want to all chanels share one DB
    def _getDb(self, channel=None):
        filename = self.filename # all channels share
        if filename in self.dbs:
            db = self.dbs[filename]
        elif os.path.exists(filename):
            db = sqlite3.connect(filename)
            self.dbs[filename] = db
        else:
            db = sqlite3.connect(filename)
            self.dbs[filename] = db

        tmap = {int:"INTEGER", str:"TEXT"}
        lines = [f'{n} {tmap[t]}' for n,t in xkcd_fields]
        lines[0] += ' PRIMARY KEY'
        body = ','.join(lines)
        sql = f'CREATE TABLE IF NOT EXISTS xkcd ( {body} );'

        cur = db.cursor()
        cur.execute(sql)
        db.commit()
        return db


    def get_latest(self):
        '''
        Get latest from xkcd
        '''
        rec = xkcd_get()
        return self.cache_add(rec)

    def get(self, num):
        '''
        Get numbered xkcd
        '''
        if num is None:
            return self.get_latest()

        req = self.cache_get(num)
        if req:
            return req

        req = xkcd_get(num)
        return self.cache_add(req)

    def cache_get(self, num):
        '''
        If cache has the number, return the record else None.
        '''
        db = self._getDb()
        cur = db.cursor()
        lst = ','.join(xkcd_field_names)
        sql = f'SELECT {lst} FROM xkcd WHERE num = ?'
        cur.execute(sql, (num,))
        res = cur.fetchall()
        db.commit()

        if len(res) == 0:
            return
        dat = xkcd_arr_to_dict(res[0])
        return XkcdRecord(**dat)


    def cache_add(self, rec, force=False):
        '''
        Add a rec to cache.  If force add unconditionally
        '''
        old = self.cache_get(rec.num)

        if not force and old:
            return old

        if old:
            self.bobby(old.num)
            
        db = self._getDb()
        cur = db.cursor()
        quests = ",".join(["?"]*len(xkcd_field_names))
        cur.execute(f"INSERT INTO xkcd values({quests})", rec.aslist);
        db.commit()
        return rec        

    def add(self, num):
        '''
        Add numbered xkcd, if needed.
        '''
        rec = self.cache_get(num)
        if rec:
            return rec
        rec = xkcd_get(num)
        return self.cache_add(rec)

    def bobby(self, num):
        'Drop the numbered cache'
        db = self._getDb()
        cur = db.cursor()
        cur.execute("""DELETE FROM xkcd WHERE num = ?""", (num,))
        db.commit()


    def cache_glob(self, pat):
        'Do a GLOB search'

        db = self._getDb()
        cur = db.cursor()
        cur.execute("SELECT num FROM xkcd WHERE title GLOB ? OR alt GLOB ?", (pat, pat))
        return [res[0] for res in cur.fetchall()]


    def cache_stats(self):
        db = self._getDb()
        cur = db.cursor()
        cur.execute("SELECT num FROM xkcd")
        nums = [res[0] for res in cur.fetchall()]
        nums.sort()
        return f'{len(nums)} in [{nums[0]}, {nums[-1]}]'

        
XkcdDB = plugins.DB("Xkcd", {'sqlite3': SqliteXkcdDB})


class XKCD(callbacks.Plugin):
    """Interface with XKCD website"""

    def __init__(self, irc):
        self.__parent = super(XKCD, self)
        self.__parent.__init__(irc)
        self.db = XkcdDB()


    def doPrivmsg(self, irc, msg):
        if ircmsgs.isCtcp(msg):
            return
        if ircmsgs.isAction(msg):
            text = ircmsgs.unAction(msg)
        else:
            text = msg.args[1]
        lines = list()
        for url in utils.web.urlRe.findall(text):
            #print(f'maybe url {url}')
            if not url.startswith(xkcd_base_url):
                continue
            r = re.search(xkcd_url_id_re, url)
            if not r:
                continue
            try:
                num = int(r[1])
            except TypeError:
                continue
            s = self.db.get(num)
            lines.append(str(s))
            #print(f'snarfed {s}')
        if lines:
            irc.reply(', '.join(lines), sendImmediately=True)

    def info(self, irc, msg, args, channel, num):
        '''<num>
        
        Return info about the numbered xkcd comic
        '''
        try:
            rec = self.db.get(num)
        except Exception as err:
            irc.error(err)
            return
        rep = str(rec)
        #print(rep)
        irc.reply(rep)
    xkcd = wrap(info, ['channeldb', optional('id')])
    info = xkcd


    def alt(self, irc, msg, args, channel, num):
        '''<num>
        
        Return the "alt" text for the given xkcd
        '''
        try:
            rec = self.db.get(num)
        except Exception as err:
            irc.error(err)
            return        
        lines = [one for one in rec.alt.split("\n") if one]
        if lines:
            irc.reply(' '.join(lines))
        else:
            irc.reply('no alt for ' + str(rec))
    alt = wrap(alt, ['channeldb', optional('id')])

    def transcript(self, irc, msg, args, channel, num):
        '''<num>
        
        Return the transcript for the given xkcd
        '''
        try:
            rec = self.db.get(num)
        except Exception as err:
            irc.error(err)
            return        
        lines = [one for one in rec.transcript.split("\n") if one]
        if lines:
            irc.reply(' '.join(lines))
        else:
            irc.reply('no transcript for ' + str(rec))
    transcript = wrap(transcript, ['channeldb', optional('id')])

    def glob(self, irc, msg, args, channel, pattern):
        '''<pattern>
        
        Return the xkcd numbers matching the pattern.
        Pattern matched against title and alt.
        '''
        nums = self.db.cache_glob(pattern)
        if not nums:
            irc.reply(f'no match for "{pattern}"')
            return
        nums.sort()
        nums = ' '.join(map(str,nums))
        irc.reply(nums)
    glob = wrap(glob, ['channeldb', 'text'])

    def stats(self, irc, msg, args):
        '''
        Print some stats about the xkcd cache
        '''
        irc.reply(self.db.cache_stats())
    stats = wrap(stats)

    # fixme, make this owner only as it can hammer on xkcd.com
    # def download(self, irc, msg, args, channel, num1, num2):
    #     '''<num1> [<num2>]
    #
    #     Refresh the cache.
    #     '''
    #     if not num2:
    #         num2 = num1 + 1
    #     for num in range(num1, num2):
    #         #self.db.bobby(num)
    #         try:
    #             rec = self.db.add(num)
    #         except Exception as err:
    #             continue
    #     irc.reply(f'downloaded {num2-num1} entries')
    # download = wrap(download, ['channeldb', 'id', optional('id')])


Class = XKCD


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
