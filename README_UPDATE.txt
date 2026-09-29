YLA update - English + French dictionary and a faster add_sentence tool

Unzip into your project root (the folder that contains data\, lexer\, parser\).
Say yes if asked to replace add_sentence.py.

Files:
  add_sentence.py               (project root)  - new version, keeps asking for sentences
  data\dictionary.csv           - about 67,000 English + French words with categories
  lexer\dictionary_loader.py    - reads the dictionary (used by lexer.py)
  tools\build_dictionary.py     - how the dictionary was built (for the report; do not need to run)

ONE manual step: add 2 lines to lexer\lexer.py, directly under this line:
    WORDS, PHRASES = _build_lexicon()
the two lines are:
    import dictionary_loader
    dictionary_loader.load_into(WORDS, strip_accents, VALID_CATEGORIES)
