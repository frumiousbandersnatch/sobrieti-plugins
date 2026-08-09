"""A small part-of-speech bigram grammar used to keep generated anagrams
at least plausibly English, rather than a random word salad.

This is not a full parser or CFG -- it is a lightweight transition graph
over coarse POS tags that is cheap to check while backtracking through
the anagram search. It is intentionally permissive: it accepts many
sequences a stricter grammar would reject, and it will occasionally
reject a valid sentence structure it doesn't model (e.g. relative
clauses). It trades linguistic completeness for speed and simplicity.
"""

DET = "DET"
PRON = "PRON"
ADJ = "ADJ"
NOUN = "NOUN"
VERB = "VERB"
ADV = "ADV"
PREP = "PREP"
CONJ = "CONJ"
AUX = "AUX"

ALL_POS = {DET, PRON, ADJ, NOUN, VERB, ADV, PREP, CONJ, AUX}

# Parts of speech a generated sentence may start with.
START_POS = {DET, PRON, NOUN, ADJ}

# Parts of speech a generated sentence may end on.
END_POS = {NOUN, VERB, ADV, ADJ}

# Allowed POS -> {allowed following POS}.
TRANSITIONS = {
    DET: {ADJ, NOUN},
    ADJ: {ADJ, NOUN},
    NOUN: {VERB, AUX, CONJ, PREP},
    PRON: {VERB, AUX},
    VERB: {DET, PRON, ADV, PREP, ADJ, NOUN, CONJ},
    AUX: {VERB, ADJ, DET, ADV, NOUN, PRON},
    ADV: {VERB, ADJ, ADV, CONJ, PREP},
    PREP: {DET, PRON, NOUN, ADJ},
    CONJ: {DET, PRON, NOUN, ADJ, VERB, AUX},
}


def allowed_next(pos):
    """POS tags permitted to follow POS (empty set if POS is unknown)."""
    return TRANSITIONS.get(pos, frozenset())


def format_sentence(words) -> str:
    """Join WORDS into a capitalized, period-terminated sentence."""
    sentence = " ".join(words)
    return sentence[0].upper() + sentence[1:] + "."
