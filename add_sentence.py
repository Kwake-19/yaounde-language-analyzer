"""
add_sentence.py
Interactive tool for the Yaoundé Language Analyzer.

Type a new sentence. If it's ACCEPTED, it's just added to the dataset (no
new vocabulary needed). If it contains UNKNOWN words, you'll be asked to
pick a category for each one - your answers are saved to
data/vocabulary.csv, the sentence is saved to data/collected_sentences.csv,
and the sentence is immediately re-checked so you can see the result.

Nothing here edits lexer.py or parser.py - it only adds rows to the two
CSV data files. That's the whole point: growing the analyzer's coverage
becomes a data task, not a coding task.

Usage (from the project root):
    python add_sentence.py
"""

import csv
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "lexer"))
sys.path.insert(0, str(PROJECT_ROOT / "parser"))

import lexer  # noqa: E402
import parser as yla_parser  # noqa: E402

DATA_CSV = PROJECT_ROOT / "data" / "collected_sentences.csv"
VOCAB_CSV = PROJECT_ROOT / "data" / "vocabulary.csv"

CATEGORY_MENU = [
    lexer.NOUN, lexer.VERB, lexer.PRONOUN, lexer.PREPOSITION, lexer.ADJECTIVE,
    lexer.GREETING_ADDRESS, lexer.DISCOURSE_MARKER, lexer.TAG_QUESTION,
    lexer.SLANG_INTERJECTION, lexer.MONEY_NUMBER, lexer.LOCATION, lexer.PARTICLE,
]


def next_sentence_id():
    if not DATA_CSV.exists():
        return 1
    with DATA_CSV.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    ids = [int(r["id"]) for r in rows if r.get("id", "").isdigit()]
    return (max(ids) + 1) if ids else 1


def append_sentence(sentence_id, topic, sentence):
    file_exists = DATA_CSV.exists()
    with DATA_CSV.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["id", "topic", "sentence"])
        writer.writerow([sentence_id, topic, sentence])


def append_vocabulary(word, category):
    file_exists = VOCAB_CSV.exists()
    with VOCAB_CSV.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["word", "category"])
        writer.writerow([word, category])


def ask_category(word):
    print("\n  Unknown word: '%s'" % word)
    for i, cat in enumerate(CATEGORY_MENU, 1):
        print("    %2d) %s" % (i, cat))
    print("     0) skip this word (leave it UNKNOWN for now)")
    while True:
        choice = input("  Category number for '%s': " % word).strip()
        if choice == "0":
            return None
        if choice.isdigit() and 1 <= int(choice) <= len(CATEGORY_MENU):
            return CATEGORY_MENU[int(choice) - 1]
        print("  Please enter a number from the list above.")


def reload_lexicon():
    """Re-read vocabulary.csv into the already-running lexer module, so a
    newly added word is usable immediately without restarting Python."""
    lexer._load_extra_vocabulary()
    lexer.MAX_PHRASE_LEN = max(len(p) for p in lexer.PHRASES)


def _run_check(sentence):
    """Adapter: works whether check_sentence() returns a dict (accepted/
    message/tagged keys) or a plain (accepted, message, tagged) tuple."""
    result = yla_parser.check_sentence(sentence)
    if isinstance(result, dict):
        return result["accepted"], result["message"], result["tagged"]
    return result


def main():
    print("=" * 60)
    print("Yaoundé Language Analyzer - Add & Test a Sentence")
    print("=" * 60)
    sentence = input("\nType a sentence to test: ").strip()
    if not sentence:
        print("Nothing entered, exiting.")
        return

    accepted, message, tagged = _run_check(sentence)
    print("\nTagged:", tagged)
    print("Result:", "ACCEPTED" if accepted else "REJECTED", "-", message)

    unknown_words = sorted({tok for tok, tag in tagged if tag == lexer.UNKNOWN})
    if unknown_words:
        print("\nThis sentence has %d unknown word(s). Let's categorize them:"
              % len(unknown_words))
        for word in unknown_words:
            category = ask_category(word)
            if category:
                append_vocabulary(word, category)
                print("  Saved: '%s' -> %s" % (word, category))
        reload_lexicon()

        print("\nRe-checking sentence with updated vocabulary...")
        accepted, message, tagged = _run_check(sentence)
        print("Tagged:", tagged)
        print("Result:", "ACCEPTED" if accepted else "REJECTED", "-", message)

    topic = input("\nTopic for this sentence (e.g. taxi_commuting), "
                   "or press Enter for 'user_submitted': ").strip()
    if not topic:
        topic = "user_submitted"
    sentence_id = next_sentence_id()
    append_sentence(sentence_id, topic, sentence)
    print("\nSaved sentence #%d to data/collected_sentences.csv" % sentence_id)
    print("Done. Run parser/parser.py anytime to see the full updated Accepted count.")


if __name__ == "__main__":
    main()
