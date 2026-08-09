"""Backtracking search for anagram sentences.

Given a multiset of letters and a POS-tagged dictionary, this searches
for sequences of words that (a) use exactly the given letters and
(b) form a POS sequence permitted by grammar.TRANSITIONS. The search
space is huge for anything but short inputs, so it is randomized and
budget-limited: it shuffles candidate words and takes whatever
grammatical, letter-exact sentences it finds before time runs out,
rather than exhaustively enumerating everything.
"""

import random
import time
from collections import Counter

from .grammar import END_POS, START_POS, allowed_next, format_sentence
from .letters import counter_to_mask

# Cap on how many dictionary words are considered per part of speech.
# Without this, common tags like NOUN can hold tens of thousands of
# entries, making every recursion step scan the whole bucket. Shorter
# words are kept preferentially since they combine more flexibly
# within a typical input's letter budget.
MAX_BUCKET_SIZE = 4000


class _WordEntry:
    __slots__ = ("word", "letters", "mask", "length")

    def __init__(self, word: str):
        self.word = word
        self.letters = Counter(word)
        self.mask = counter_to_mask(self.letters)
        self.length = len(word)


def build_pos_buckets(pos_map, max_bucket_size: int = MAX_BUCKET_SIZE):
    """Group POS_MAP (word -> {tags}) into {tag: [word entries]}, length-capped."""
    raw: dict[str, list[_WordEntry]] = {}
    for word, tags in pos_map.items():
        entry = _WordEntry(word)
        for tag in tags:
            raw.setdefault(tag, []).append(entry)

    buckets = {}
    for tag, entries in raw.items():
        entries.sort(key=lambda e: e.length)
        buckets[tag] = entries[:max_bucket_size]
    return buckets


def generate_anagrams(
    text_letters: Counter,
    pos_buckets,
    number: int = 1,
    max_words: int = 6,
    time_budget: float = 8.0,
    rng=None,
):
    """Search for up to NUMBER unique grammatical anagram sentences of TEXT_LETTERS."""
    rng = rng or random.Random()
    total_letters = sum(text_letters.values())
    if total_letters == 0:
        return []

    results: list[str] = []
    seen: set[str] = set()
    deadline = time.monotonic() + time_budget

    def search(remaining, remaining_mask, remaining_total, last_pos, words):
        if time.monotonic() > deadline or len(results) >= number:
            return
        if remaining_total == 0:
            if last_pos in END_POS and words:
                sentence = format_sentence(words)
                if sentence not in seen:
                    seen.add(sentence)
                    results.append(sentence)
            return
        if len(words) >= max_words:
            return

        candidate_tags = allowed_next(last_pos) if last_pos is not None else START_POS
        for tag in candidate_tags:
            for entry in shuffled_buckets.get(tag, ()):
                if entry.length > remaining_total:
                    continue
                if entry.mask & ~remaining_mask:
                    continue
                ok = True
                for ch, count in entry.letters.items():
                    if remaining.get(ch, 0) < count:
                        ok = False
                        break
                if not ok:
                    continue

                new_remaining = dict(remaining)
                for ch, count in entry.letters.items():
                    left = new_remaining[ch] - count
                    if left:
                        new_remaining[ch] = left
                    else:
                        del new_remaining[ch]
                new_mask = counter_to_mask(new_remaining)

                words.append(entry.word)
                search(new_remaining, new_mask, remaining_total - entry.length, tag, words)
                words.pop()

                if len(results) >= number or time.monotonic() > deadline:
                    return

    attempts = 0
    max_attempts = 50
    while len(results) < number and attempts < max_attempts and time.monotonic() < deadline:
        attempts += 1
        shuffled_buckets = {}
        for tag, entries in pos_buckets.items():
            shuffled = list(entries)
            rng.shuffle(shuffled)
            shuffled_buckets[tag] = shuffled
        search(dict(text_letters), counter_to_mask(text_letters), total_letters, None, [])

    return results[:number]
