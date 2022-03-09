#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
An n-char clone of the wordle game.
'''

import re
import sqlite3

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
    for n,words in enumerate(splitn(open(filename).read().split('\n'), maxlen)):
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


def markdup(word, codes, theme = 'term'):
    '''
    Take word and codes and return word marked up according to theme
    '''
    letters = themes[theme]
    word = word.lower()
    a = ord('a')
    ret = ' '.join([letters[c][ord(l)-a] for l,c in zip(word, codes)])
    if theme == 'term':
        return ret
    return '\x02' + ret + '\x03'

def codify(guess, word):
    '''
    Return codes for guess compared to word.
    '''
    codes = [0]*len(guess)
    for index, (have, want) in enumerate(zip(guess, word)):
        if have == want:
            codes[index] = 2
            continue
        if have in word:
            codes[index] = 1
            continue
    return codes

# class Game:
#     def __init__(self, word, theme = 'term'):
#         self._word = word
#         self._theme = theme
#         self._len = len(word)
#         self._guesses = list()

#     def __len__(self):
#         return len(self._guesses)

#     def compare(self, word):
#         '''
#         Return code list comparing word.
#         '''
#         codes = [0]*self._len
#         if len(word) != self._len:
#             return codes
#         for index, (have, want) in enumerate(zip(word, self._word)):
#             if have == want:
#                 codes[index] = 2
#                 continue
#             if have in self._word:
#                 codes[index] = 1
#                 continue
#         return codes

#     def guess(self, word):
#         '''
#         Add a guess, return pair (True/false, coding)
#         '''
#         self._guesses.append(word)
#         codes = self.compare(word)
#         return word == self._word, coded_word(word, codes, self._theme)

#     def board(self):
#         '''
#         Return list of lines for all past guesses
#         '''
#         lines = list()
#         for word in self._guesses:
#             codes = self.compare(word)
#             line = (word == self._word, coded_word(word, codes, self._theme))
#             lines.append(line)
#         return lines
            

class Field:
    '''
    The playing field for Nordl games.

    This manages play through a persistent database.

    The "nick" is a single nick name or "*" meaning multiplayer.

    The "chan" is a channel name or "*" meaning play from any channel.  

    The words are also taken from the DB.  Call .load(file_or_list) to fill.

    '''

    def __init__(self, dbname):
        self.db = sqlite3.connect(dbname)
        cur = self.db.cursor()

        # Words determine fodder for games and guesses and may be of
        # any length.
        cur.execute("""
        CREATE TABLE IF NOT EXISTS words (word TEXT NOT NULL UNIQUE)
        """)
        cur.execute("""
        CREATE INDEX IF NOT EXISTS word_index ON words(word)
        """)

        # A game answer is a first "guess" with game_id NULL.
        # A non-NULL game_id is the ID of the game answer.
        cur.execute("""
        CREATE TABLE IF NOT EXISTS guess (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        game_id      INTEGER DEFAULT NULL,
        word         TEXT NOT NULL,
        nick          TEXT NOT NULL,
        chan         TEXT NOT NULL,
        time         DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(game_id) REFERENCES guess(id))""")

        # A verdict is created when a guess is correct (outcome is
        # True) or the game is abandoned (outcome is False).  The
        # game_id points to a parentless guess.
        cur.execute("""
        CREATE TABLE IF NOT EXISTS verdict (
        guess_id     INTEGER NOT NULL UNIQUE,
        outcome      BOOLEAN NOT NULL,
        FOREIGN KEY(guess_id) REFERENCES guess(id))""")
        self.db.commit()
        return


    def load(self, words):
        '''
        Add words to DB.

        words may be a list of strings, giving words directly or a
        string filename or an open file object of words, one per line.
        '''
        if isinstance(words, str):
            words = open(words).read().split("\n")
        elif hasattr(words, "read"):
            words = words.read().split("\n")
        cur = self.db.cursor()
        for word in words:
            cur.execute("""
            INSERT OR IGNORE INTO words(word) VALUES(?)""", (word,))
        self.db.commit()


    def start(self, word_or_length, nick="*", chan="*"):
        '''
        Start a new game, return its game ID for later lookup.

        If word_or_length is a string, use it as the word to guess.
        If an integer, select a random word of that length.

        Raise ValueError if no word of given length can be found.
        '''
        cur = self.db.cursor()
        if isinstance(word_or_length, int):
            word = cur.execute("""
            SELECT word FROM words WHERE length(word) = ?
            ORDER BY RANDOM() LIMIT 1
            """, (word_or_length,)).fetchone()[0]
            print(f'chose word: "{word}"')
        else:
            word = word_or_length
        if word is None:
            raise ValueError("no target word")

        print(f'"{word}","{nick}","{chan}"')
        cur.execute("""
        INSERT INTO guess(word,nick,chan) VALUES(?,?,?)""",
                    (word, nick, chan))
        self.db.commit()
        return cur.lastrowid

    def game_data(self, gid):
        '''
        Get game data.

        Return tuple (oc, gs).

            - oc :: outcome is True if game won, False if give up,
              None if stop open

            - gs :: list of guess tuple: (word, nick, chan, time)
        '''
        cur = self.db.cursor()
        gs = cur.execute("""
        SELECT word, nick, chan, time FROM guess
        WHERE id = ? OR game_id = ?
        ORDER BY time""", (gid, gid)).fetchall()
        if not gs:
            raise IndexError
        oc = self.game_status(gid)
        return (oc, gs)


    def game_status(self, gid):
        '''
        Return game status: True: solved, False: gave up.  None: not complete.
        '''
        cur = self.db.cursor()
        oc = cur.execute("""
        SELECT verdict.outcome FROM verdict
        INNER JOIN guess ON guess.id = verdict.guess_id
        WHERE guess.game_id=? OR (guess.id=? AND guess.game_id is NULL)""",
                        (gid,gid)).fetchone()
        if not oc:
            return 
        return oc[0] == 1
        

    def game_info(self, gid):
        '''
        Get game info as tuple (gid, word, nick, chan, time)
        '''
        cur = self.db.cursor()
        gi = cur.execute("""
        SELECT id, word, nick, chan, time FROM guess
        WHERE id = ? AND game_id IS NULL 
        LIMIT 1""", (gid,)).fetchone()
        if not gi:
            raise IndexError
        return gi

    def answer(self, gid):
        '''
        Return correct answer for game ID or raise IndexError.
        '''
        cur = self.db.cursor()
        want = cur.execute("""
        SELECT word FROM guess WHERE id=? and game_id is NULL
        """, (gid,)).fetchone()
        if want is None:
            raise IndexError(f'no game with ID {gid}')
        return want[0]

    def answer_check(self, gid, nick="*", chan="*"):
        '''
        Return answer word for gid, checking nick/chan.
        '''
        _, want, thenick, thechan, _ = self.game_info(gid)
        if thenick not in ("*", nick):
            raise ValueError(f'this game is played by "{thenick}"')
        if thechan not in ("*", chan):
            raise ValueError(f'this game is played in "{thechan}"')
        return want

    def guess(self, gid, word, nick="*", chan="*"):
        '''
        Attempt a guess.  Return True if success, else false.

        A correct guess will finalize the game.

        Raise IndexError if gid does not exist or is closed.

        Raise ValueError if nick or chan is not allowed.
        '''
        if self.game_status(gid) is not None:
            raise IndexError('this game is played')

        want = self.answer_check(gid, nick, chan)

        cur = self.db.cursor()
        cur.execute("""
        INSERT INTO guess(game_id,word,nick,chan) VALUES(?,?,?,?)""",
                    (gid, word, nick, chan))
        last_gid = cur.lastrowid

        solved = want == word
        if solved:
            cur.execute("""
            INSERT INTO verdict(guess_id,outcome) VALUES(?,?)""",
                        (last_gid, True))
        self.db.commit()
        return solved

    def scores(self, chan=None):
        '''
        Return leaderboard up to given length.
        If where is given, limit to games plaed there.
        Return list of tuples: [(nwins,nplays,nick), ...]
        '''
        cur = self.db.cursor()
        extra = f"AND chan='{chan}'" if chan else ""
        
        nick_guesses = {n:g for n,g in cur.execute(f"""
        SELECT nick,COUNT(nick) FROM guess WHERE game_id is NULL {extra} GROUP BY nick
        """).fetchall()}

        nick_correct = {n:c for n,c in cur.execute(f"""
        SELECT guess.nick,count(guess.nick) FROM guess
        INNER JOIN verdict ON verdict.guess_id = guess.id
        WHERE verdict.outcome=True {extra}
        GROUP BY guess.nick""").fetchall()}

        return {n:(g, nick_correct.get(n, 0)) for n,g in nick_guesses.items()}

        

    def last(self, nick="*", chan="*"):
        '''
        Return most recent game ID. 

        Raise IndexError if no match.
        '''
        cur = self.db.cursor()
        gid = cur.execute("""
        SELECT id FROM guess
        WHERE game_id IS NULL AND nick=? AND chan=?
        ORDER BY time DESC LIMIT 1""", (nick, chan)).fetchone()
        if gid is None:
            raise IndexError(f'no recent game for nick="{nick}", chan="{chan}"')
        return gid[0]


    def last_guess(self, gid):
        '''
        Return the ID of the last guess for game ID.
        '''
        cur = self.db.cursor()
        last = cur.execute("""
        SELECT id FROM guess
        WHERE (id=? AND game_id is NULL) OR game_id=?
        ORDER BY time DESC LIMIT 1""", (gid,gid)).fetchone()
        if last is None:
            raise IndexError(f'no game ID #{gid}')
        return last[0]


    def giveup(self, gid, nick="*", chan="*"):
        '''
        Give up on a game, finalizing it and returning answer.

        Raise IndexError if gid does not exist.
        '''
        if self.game_status(gid) is not None:
            raise IndexError('this game is played')

        wanted = self.answer_check(gid, nick, chan)
        last_gid = self.last_guess(gid)

        cur = self.db.cursor()
        cur.execute("""
        INSERT INTO verdict(guess_id,outcome) VALUES(?,?)""",
                    (last_gid, False))
        self.db.commit()
        return wanted

if __name__ == "__main__":
    import os, sys
    f = Field(sys.argv[1])
    for one in sys.argv[2:]:
        if os.path.exists(one):
            print(f'load file: {one}')
            f.load(one)
        else:
            print(f'load word: {one}')
            f.load([one])
