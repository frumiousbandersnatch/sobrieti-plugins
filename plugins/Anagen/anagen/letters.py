"""Letter-multiset utilities for anagram matching."""

import re
from collections import Counter

_NON_LETTER_RE = re.compile(r"[^a-z]")


def normalize_text(text: str) -> str:
    """Lowercase TEXT and strip everything but a-z letters."""
    return _NON_LETTER_RE.sub("", text.lower())


def letter_counter(text: str) -> Counter:
    """Return a Counter of the letters in TEXT (spaces/punctuation ignored)."""
    return Counter(normalize_text(text))


def counter_to_mask(counter) -> int:
    """Bitmask (bit i = letter chr(97+i)) of the letters present in COUNTER."""
    mask = 0
    for ch, count in counter.items():
        if count > 0:
            mask |= 1 << (ord(ch) - 97)
    return mask
