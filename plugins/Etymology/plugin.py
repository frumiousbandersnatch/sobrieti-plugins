from urllib.parse import urlencode

from re import sub
from requests import get
from html import unescape

from supybot.commands import *



import supybot.callbacks as callbacks


def lookup(word):
    from socket import setdefaulttimeout
    setdefaulttimeout(60)
    url = "http://www.etymonline.com/search?%s" \
        % urlencode({'q':word})

    ety = get(url)
    if ety.status_code != 200:
        return "%s not found" % word

    # thank you sopel hackers!
    # https://github.com/sopel-irc/sopel/pull/1432/files
    # Let's find it
    start = ety.text.find("word__defination")
    start = ety.text.find("<p>", start)
    stop = ety.text.find("</p>", start)
    sentence = ety.text[start + 3:stop]
    # Clean up
    sentence = unescape(sentence)
    sentence = sub('<[^<]+?>', '', sentence)

    maxlength = 275
    if len(sentence) > maxlength:
        sentence = sentence[:maxlength]
        words = sentence[:-5].split(' ')
        words.pop()

        sentence = ' '.join(words) + ' […]'
    return sentence + ' - ' + url

class Etymology(callbacks.Privmsg):

    def etym(self,irc,msg,args):
        """etym <word> lookup the etymology for a word/phrase
        """
        etymology = lookup(''.join(args))
        irc.reply(etymology)

Class = Etymology 

