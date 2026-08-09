"""Build and cache a part-of-speech-tagged word dictionary.

A plain wordlist like /usr/share/dict/words has no notion of noun vs.
verb vs. adjective, which is needed to keep generated anagrams
grammatical. This module cross-references such a wordlist against
WordNet (via NLTK) to tag each word with the parts of speech it can
serve as, plus a small hand-written table of closed-class function
words (determiners, pronouns, prepositions, ...) that WordNet doesn't
usefully cover. The result is cached under the user's cache directory
so it only needs to be built once per source wordlist.
"""

import hashlib
import json
import os
import re
from pathlib import Path

DEFAULT_DICTIONARY = "/usr/share/dict/words"

_WORD_RE = re.compile(r"^[a-z]+$")

# Closed-class function words. WordNet either omits these or tags them
# uselessly (e.g. "the" has zero synsets), so they are listed by hand.
FUNCTION_WORDS = {
    "the": {"DET"}, "a": {"DET"}, "an": {"DET"},
    "this": {"DET", "PRON"}, "that": {"DET", "PRON", "CONJ"},
    "these": {"DET"}, "those": {"DET"},
    "my": {"DET"}, "your": {"DET"}, "his": {"DET", "PRON"}, "her": {"DET", "PRON"},
    "its": {"DET"}, "our": {"DET"}, "their": {"DET"},
    "some": {"DET"}, "any": {"DET"}, "no": {"DET"}, "every": {"DET"}, "each": {"DET"}, "all": {"DET"},
    "i": {"PRON"}, "you": {"PRON"}, "he": {"PRON"}, "she": {"PRON"}, "it": {"PRON"},
    "we": {"PRON"}, "they": {"PRON"}, "me": {"PRON"}, "him": {"PRON"}, "us": {"PRON"}, "them": {"PRON"},
    "who": {"PRON"}, "what": {"PRON"},
    "in": {"PREP"}, "on": {"PREP"}, "at": {"PREP"}, "by": {"PREP"}, "for": {"PREP"}, "with": {"PREP"},
    "about": {"PREP"}, "against": {"PREP"}, "between": {"PREP"}, "into": {"PREP"}, "through": {"PREP"},
    "during": {"PREP"}, "before": {"PREP", "CONJ"}, "after": {"PREP", "CONJ"},
    "above": {"PREP"}, "below": {"PREP"}, "to": {"PREP"}, "from": {"PREP"},
    "up": {"PREP", "ADV"}, "down": {"PREP", "ADV"}, "of": {"PREP"}, "off": {"PREP", "ADV"},
    "over": {"PREP"}, "under": {"PREP"}, "out": {"PREP", "ADV"},
    "and": {"CONJ"}, "but": {"CONJ"}, "or": {"CONJ"}, "nor": {"CONJ"}, "so": {"CONJ", "ADV"}, "yet": {"CONJ", "ADV"},
    "is": {"AUX"}, "was": {"AUX"}, "are": {"AUX"}, "were": {"AUX"}, "am": {"AUX"},
    "be": {"AUX"}, "been": {"AUX"}, "being": {"AUX"},
    "has": {"AUX"}, "have": {"AUX"}, "had": {"AUX"},
    "do": {"AUX"}, "does": {"AUX"}, "did": {"AUX"},
    "will": {"AUX"}, "would": {"AUX"}, "can": {"AUX"}, "could": {"AUX"},
    "shall": {"AUX"}, "should": {"AUX"}, "may": {"AUX"}, "might": {"AUX"}, "must": {"AUX"},
    "not": {"ADV"},
}

# WordNet POS codes -> our grammar tags. 'a' (adjective) and 's'
# (satellite adjective) both collapse to ADJ.
_WORDNET_POS_MAP = {"n": "NOUN", "v": "VERB", "a": "ADJ", "s": "ADJ", "r": "ADV"}


def get_cache_dir() -> Path:
    """The directory anagen caches its specialized dictionary and NLTK data in."""
    if override := os.environ.get("ANAGEN_CACHE_DIR"):
        cache_dir = Path(override)
    else:
        base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
        cache_dir = Path(base) / "anagen"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _cache_file_for(dictionary_path: str, cache_dir: Path) -> Path:
    key = hashlib.sha256(str(Path(dictionary_path).resolve()).encode()).hexdigest()[:16]
    return cache_dir / f"pos_dictionary_{key}.json"


def load_specialized_dictionary(dictionary_path: str, cache_dir: Path):
    """Load the cached POS dictionary for DICTIONARY_PATH, or None if absent/stale."""
    cache_file = _cache_file_for(dictionary_path, cache_dir)
    if not cache_file.exists():
        return None
    try:
        data = json.loads(cache_file.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    try:
        src_mtime = Path(dictionary_path).stat().st_mtime
    except OSError:
        return None
    if data.get("source_mtime") != src_mtime:
        return None
    return {word: set(tags) for word, tags in data["words"].items()}


def _ensure_wordnet(cache_dir: Path) -> None:
    """Make sure the NLTK WordNet corpus is available, downloading it if needed."""
    import nltk

    nltk_dir = cache_dir / "nltk_data"
    nltk_dir.mkdir(parents=True, exist_ok=True)
    nltk_dir_str = str(nltk_dir)
    # nltk's downloader only writes into directories already registered in
    # nltk.data.path, so it must be added before nltk.download() is called.
    if nltk_dir_str not in nltk.data.path:
        nltk.data.path.insert(0, nltk_dir_str)

    for package in ("wordnet", "omw-1.4"):
        try:
            nltk.data.find(f"corpora/{package}")
        except LookupError:
            nltk.download(package, download_dir=nltk_dir_str, quiet=True)


def build_specialized_dictionary(dictionary_path: str, cache_dir: Path, force: bool = False):
    """Build (or load a cached) word -> {POS tags} dictionary for DICTIONARY_PATH."""
    if not force:
        cached = load_specialized_dictionary(dictionary_path, cache_dir)
        if cached is not None:
            return cached

    _ensure_wordnet(cache_dir)
    from nltk.corpus import wordnet as wn

    base_words = set()
    with open(dictionary_path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            word = line.strip().lower()
            if _WORD_RE.match(word):
                base_words.add(word)

    pos_map: dict[str, set[str]] = {word: set(tags) for word, tags in FUNCTION_WORDS.items()}

    for wordnet_pos, tag in _WORDNET_POS_MAP.items():
        for lemma in wn.all_lemma_names(pos=wordnet_pos):
            lemma = lemma.lower()
            # Very short WordNet lemmas are overwhelmingly abbreviations and
            # single-letter symbols (e.g. "r", "li"), not usable words.
            if len(lemma) < 3 or not _WORD_RE.match(lemma):
                continue
            if lemma not in base_words and lemma not in FUNCTION_WORDS:
                continue
            pos_map.setdefault(lemma, set()).add(tag)

    cache_file = _cache_file_for(dictionary_path, cache_dir)
    payload = {
        "source_dictionary": str(Path(dictionary_path).resolve()),
        "source_mtime": Path(dictionary_path).stat().st_mtime,
        "words": {word: sorted(tags) for word, tags in pos_map.items()},
    }
    cache_file.write_text(json.dumps(payload))
    return pos_map
