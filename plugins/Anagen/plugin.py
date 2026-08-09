###
# Copyright (c) 2026, Frumious Bandersnatch
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

from supybot import utils, plugins, ircutils, callbacks
from supybot.commands import *
from supybot.i18n import PluginInternationalization

from .anagen.dictionary import (
    build_specialized_dictionary,
    get_cache_dir,
    load_specialized_dictionary,
)
from .anagen.generator import build_pos_buckets, generate_anagrams
from .anagen.letters import letter_counter


_ = PluginInternationalization('Anagen')


class Anagen(callbacks.Plugin):
    """Anagram generator"""
    threaded = True

    def __init__(self, irc):
        super().__init__(irc)
        # Keyed by dictionary path, since it's reconfigurable at runtime.
        self._pos_buckets_cache = {}

    def _pos_buckets(self, irc, dictionary_path):
        buckets = self._pos_buckets_cache.get(dictionary_path)
        if buckets is not None:
            return buckets

        cache_dir = get_cache_dir()
        pos_map = load_specialized_dictionary(dictionary_path, cache_dir)
        if pos_map is None:
            irc.reply(
                "No anagram dictionary cached yet for %s; building one "
                "now, this may take a while..." % dictionary_path,
                prefixNick=False,
            )
            pos_map = build_specialized_dictionary(dictionary_path, cache_dir)

        buckets = build_pos_buckets(pos_map)
        self._pos_buckets_cache[dictionary_path] = buckets
        return buckets

    def ana(self, irc, msg, args, text):
        """<text>

        Reply with one grammatically-plausible anagram of <text>.
        """
        counts = letter_counter(text)
        if not counts:
            irc.reply("That has no letters in it to anagram.")
            return

        dictionary_path = self.registryValue('dictionary')
        buckets = self._pos_buckets(irc, dictionary_path)
        results = generate_anagrams(
            counts, buckets, number=1,
            max_words=self.registryValue('maxWords'),
            time_budget=self.registryValue('timeBudget'),
        )
        if not results:
            irc.reply("Couldn't find an anagram of that in time.")
            return
        irc.reply(results[0], prefixNick=False)
    ana = wrap(ana, ['text'])


Class = Anagen


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
