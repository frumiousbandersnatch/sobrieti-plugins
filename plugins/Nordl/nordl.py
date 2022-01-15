#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
An n-char clone of the wordle game.
'''

import re

# match non-proper-noun and ascii letters
simple_word = re.compile(f'^[a-z]+$')

def check_word(word, maxlen=9):
    '''
    Return a suitable derived word or None
    '''
    if len(word) > maxlen:
        return
    if simple_word.match(word):
        return word
    return 


def splitn(words, maxlen=9):
    '''
    Given list of words, return list of list of words with index
    giving word lengths, up to maxlen.
    '''
    keep = [set() for _ in range(maxlen+1)]
    for word in words:
        word = check_word(word, maxlen)
        if not word:
            continue
        keep[len(word)].add(word)
    ret = list()
    for one in keep:
        one = list(one)
        one.sort()
        ret.append(tuple(one))
    return ret
    
def genfiles(maxlen=9, filename='/usr/share/dict/words', outpat='words-%d'):
    '''
    Generate per-length word files from /usr/share/dict/words
    '''
    for n,words in enumerate(splitn(open(filename).read().split('\n'))):
        if not n:
            continue
        open(outpat % n, "w").write('\n'.join(words))
    

def tty_color_letters(fg,bg):
    if bg == 'yellow':
        return [chr(0x1f130 + n) for n in range(26)]
    if bg == 'green':
        return [chr(0x1f170 + n) for n in range(26)]
    return [chr(ord('A') + n) for n in range(26)]
    

# https://modern.ircdocs.horse/formatting.html
try:
    from supybot import ircutils
    def irc_color_letters(fg, bg):
        return [ircutils.mircColor(chr(ord('A') + n), fg, bg)
                for n in range(26)]
except ImportError:
    irc_color_letters = tty_color_letters
    
themes = dict(

    term = [tty_color_letters("white","black"),
            tty_color_letters("black","yellow"),
            tty_color_letters("white","green")],

    dark = [irc_color_letters("white","black"),
            irc_color_letters("black","yellow"),
            irc_color_letters("black","green")],

    lite = [irc_color_letters("black","white"),
            irc_color_letters("black","yellow"),
            irc_color_letters("black","green")],
)


def coded_word(word, codes, theme = 'term'):
    letters = themes[theme]
    word = word.lower()
    a = ord('a')
    ret = ''.join([letters[c][ord(l)-a] for l,c in zip(word, codes)])
    if theme == 'term':
        return ret
    return '\x02' + ret + '\x03'

class Game:
    def __init__(self, word, theme = 'term'):
        self._word = word
        self._theme = theme
        self._len = len(word)
        self._guesses = list()

    def __len__(self):
        return len(self._guesses)

    def compare(self, word):
        '''
        Return code list comparing word.
        '''
        codes = [0]*self._len
        if len(word) != self._len:
            return codes
        for index, (have, want) in enumerate(zip(word, self._word)):
            if have == want:
                codes[index] = 2
                continue
            if have in self._word:
                codes[index] = 1
                continue
        return codes

    def guess(self, word):
        '''
        Add a guess, return pair (True/false, coding)
        '''
        self._guesses.append(word)
        codes = self.compare(word)
        return word == self._word, coded_word(word, codes, self._theme)

    def board(self):
        '''
        Return list of lines for all past guesses
        '''
        lines = list()
        for word in self._guesses:
            codes = self.compare(word)
            line = (word == self._word, coded_word(word, codes, self._theme))
            lines.append(line)
        return lines
            
