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
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks


import os
from glob import glob
import json
import re

def loads(string):
    """
    Load the string into a Python object.  

    The string will be interpreted as JSON or failing that as Python.
    
    Note: only pass trusted strings!
    """
    lines = []
    for line in string.split('\n'):
        sline = line.strip()
        if not sline: continue
        if sline.startswith('#'): continue
        lines.append(line)
    if not lines:
        return
    string = '\n'.join(lines)

    try:
        data = json.loads(string)
    except ValueError:
        data = None
    else:
        return data
        
    return eval(string)

class SurveyObject(object):
    def __init__(self, fname):
        string = open(fname).read()
        self.__dict__.update(loads(string))
        return
    pass

class Surveyor(object):
    def __init__(self, survey):
        self.survey = survey
        self.current = -1
        self.answers = []
        self.score = 0
        return

    def say(self, irc, string):
        irc.reply(string, prefixNick=False, private=True)

    def __call__(self, irc, answer=None):
        if answer:
            qa = self.survey.questions[self.current]
            if qa['a']:
                number = int(answer)
                if number <1 or number > len(qa['a']):
                    self.say(irc, 'Not a valid answer')
                    return False
                index = number-1
                a = qa['a'][index]
                self.score += a[0]

            self.answers.append(answer)

        self.current += 1        
        if self.current >= len(self.survey.questions):
            self.finish(irc, True)
            return True

        qa = self.survey.questions[self.current]
        irc.reply(qa['q'], prefixNick=False, private=True)
        if not qa['a']:
            prompt = '(answer by typing "answer <free form text>")'
        else:
            ans = ['[%d] %s' % (n+1,a[1]) for n,a in enumerate(qa['a'])]
            prompt = ' | '.join(ans)
            prompt += ' (answer by typing "answer #")'

        self.say(irc, prompt)

        return False

    def finish(self, irc, finished = False):
        if not finished:
            self.say(irc, 'Survey aborted')

        ans = ', '.join(['[%s]'%a for a in self.answers])
        self.say(irc, 'Answers: %s' % ans)
        self.say(irc, 'Score: %d' % self.score)
        return

    pass
    

class Survey(callbacks.Plugin):
    """Take a survey"""
    threaded = True

    def __init__(self, irc):
        super(Survey,self).__init__(irc)

        sd = self.registryValue('surveyDir')
        if not sd:
            sd = os.path.join(os.path.dirname(__file__),'surveys')
        self.survey_dir = sd

        self._surveys = {}      # filename->SurveyObject
        self._open_surveyors = {} # nick->Surveyor
        return

    def _try_add_survey_file(self, fname):
        'Try to add the survey file'
        if fname in self._surveys.keys(): 
            return
        self._surveys[fname] = SurveyObject(fname)

    def _load_surveys(self):
        'Load all surveys in configured directory.'
        for fname in glob(os.path.join(self.survey_dir,'*.survey')):
            self._try_add_survey_file(fname)
        return

    def _find(self, pat):
        found = []
        for s in self._surveys.values():
            if re.search(pat, s.title, flags=re.I):
                found.append(s)
        return found

    def list(self, irc, msg, args):
        """List available surveys"""
        self._load_surveys()
        if not self._surveys:
            irc.reply('No surveys known')
            return
        slist = ', '.join(['"%s"'%s.title for s in self._surveys.values()])
        irc.reply('I can administer these surveys: %s' % slist)
        return
    list = wrap(list, [])

    def describe(self, irc, msg, args, pattern):
        """<pattern>

        Describe surveys with title matching the (regex) pattern"""
        self._load_surveys()
        found = self._find(pattern)
        if not found:
            irc.reply('No survey found matching "%s"'%pattern)
            return
        rep = ['"%s": %s' % (s.title,s.desc) for s in found]
        rep = ' | '.join(rep)
        irc.reply(rep)
        return
    describe = wrap(describe, ['anything'])

    def start(self, irc, msg, args, pattern):
        """<pattern>

        Start taking the survey that matches the (regex) <pattern>."""

        already = self._open_surveyors.get(msg.nick)
        if already:
            self._open_surveyors.pop(key)
            already.finish(irc)

        self._load_surveys()
        found = self._find(pattern)
        if len(found) != 1:
            irc.reply('Your pattern "%s" does not uniquely specify a survey, '
                      'try to be more specific.' % pattern)
            return

        survey = found[0]

        surveyor = Surveyor(survey)
        self._open_surveyors[msg.nick] = surveyor

        irc.reply('Check for a private message from me')
        done = surveyor(irc)
        if done: 
            self._open_surveyors.pop(msg.nick)
        return
    start = wrap(start, ['anything'])

    def answer(self, irc, msg, args, text):
        """<text>

        Provide an answer to a recently asked survey question.
        """
        if irc.isChannel(msg.args[0]):
            irc.reply("For your privacy, answers are only accepted in a PM. "
                      "Start one by typing: /query %s" % irc.nick)
            return

        surveyor = self._open_surveyors.get(msg.nick)
        if not surveyor:
            irc.reply('You have no open surveys. '
                      'use "survey start <name>" to start one.')
            return

        done = surveyor(irc, text)
        if done: 
            self._open_surveyors.pop(msg.nick)
        return 
    answer = wrap(answer, ['text'])
        


Class = Survey


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
