"""
dictionary_loader.py
Loads data/dictionary.csv - a general English + French vocabulary (about 67,000
common words, each already assigned one of the analyzer's categories).

It is a FALLBACK only: a word is added only if the lexer does not already know
it. So the hand-built lexicon in lexer.py and your own data/vocabulary.csv
always win over the dictionary.

lexer.py calls load_into() once, right after it builds its own word table.
"""

import csv
from pathlib import Path

DICTIONARY_CSV = Path(__file__).resolve().parent.parent / "data" / "dictionary.csv"


def load_into(words, strip_accents, valid_categories):
    """Add dictionary words to `words` (a dict: word -> category), skipping any
    word that is already there. Returns how many words were added."""
    if not DICTIONARY_CSV.exists():
        return 0
    added = 0
    with DICTIONARY_CSV.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            word = strip_accents((row.get("word") or "").strip().lower())
            category = (row.get("category") or "").strip()
            if word and category in valid_categories and word not in words:
                words[word] = category
                added += 1
    return added
