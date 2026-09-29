"""
add_sentence.py
Interactive tool for the Yaoundé Language Analyzer.

Type a sentence and see whether it is ACCEPTED or REJECTED. It keeps asking for
new sentences until you type q, so you never have to restart it.

  * unknown word  -> you pick its category (number or name); it is saved to
                     data/vocabulary.csv and the sentence is checked again
  * wrong tag     -> if a sentence is still rejected, you can correct the tag
                     of any word; the correction is saved the same way
  * every sentence you test is saved to data/collected_sentences.csv

Nothing here edits lexer.py or parser.py - growing the analyzer is a data task.

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


# ---------------------------------------------------------------- data files
def next_sentence_id():
    if not DATA_CSV.exists():
        return 1
    with DATA_CSV.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    ids = [int(r["id"]) for r in rows if (r.get("id") or "").isdigit()]
    return (max(ids) + 1) if ids else 1


def append_row(path, header, row):
    new_file = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if new_file:
            writer.writerow(header)
        writer.writerow(row)


def save_sentence(topic, sentence):
    sentence_id = next_sentence_id()
    append_row(DATA_CSV, ["id", "topic", "sentence"], [sentence_id, topic, sentence])
    return sentence_id


def save_word(word, category):
    append_row(VOCAB_CSV, ["word", "category"], [word, category])


# ---------------------------------------------------------------- checking
def reload_lexicon():
    """Re-read vocabulary.csv so a word added a moment ago is used immediately."""
    lexer._load_extra_vocabulary()
    lexer.MAX_PHRASE_LEN = max(len(p) for p in lexer.PHRASES)


def run_check(sentence):
    """Works whether check_sentence() returns a dict or a (accepted, message, tagged) tuple."""
    result = yla_parser.check_sentence(sentence)
    if isinstance(result, dict):
        return result["accepted"], result["message"], result["tagged"]
    return result


def show_result(sentence):
    accepted, message, tagged = run_check(sentence)
    print("  " + "  ".join("%s/%s" % (tok, tag) for tok, tag in tagged))
    if accepted:
        print("  ACCEPTED")
    else:
        unknown = [tok for tok, tag in tagged if tag == lexer.UNKNOWN]
        if unknown:
            print("  REJECTED - unknown word(s): " + ", ".join(unknown))
        else:
            print("  REJECTED - " + message.split(";")[0])
    return accepted, tagged


# ---------------------------------------------------------------- asking the user
def print_menu():
    print("  Categories:")
    for start in range(0, len(CATEGORY_MENU), 4):
        chunk = CATEGORY_MENU[start:start + 4]
        print("    " + "   ".join("%2d %-19s" % (start + i + 1, c) for i, c in enumerate(chunk)))
    print("    0 = skip.  You can also type the name, e.g. noun, verb, adj, prep, slang")


def parse_category(text):
    text = text.strip().upper()
    if text == "0":
        return "SKIP"
    if text.isdigit() and 1 <= int(text) <= len(CATEGORY_MENU):
        return CATEGORY_MENU[int(text) - 1]
    if text in CATEGORY_MENU:
        return text
    matches = [c for c in CATEGORY_MENU if text and c.startswith(text)]
    return matches[0] if len(matches) == 1 else None


def ask_category(word):
    while True:
        answer = input("  '%s' is a: " % word)
        category = parse_category(answer)
        if category == "SKIP":
            return None
        if category:
            return category
        print("  Not recognised - type a number from the list, or a name like noun / verb.")


# ---------------------------------------------------------------- one sentence
def handle_sentence(sentence, last_topic):
    accepted, tagged = show_result(sentence)

    unknown_words = sorted({tok for tok, tag in tagged if tag == lexer.UNKNOWN})
    menu_shown = False
    if unknown_words:
        print("\n  %d unknown word(s) - choose a category for each:" % len(unknown_words))
        print_menu()
        menu_shown = True
        changed = False
        for word in unknown_words:
            category = ask_category(word)
            if category:
                save_word(word, category)
                changed = True
        if changed:
            reload_lexicon()
            print("\n  Checking again:")
            accepted, tagged = show_result(sentence)

    # a still-rejected sentence may be caused by a wrong tag from the dictionary
    while not accepted:
        word = input("\n  Is a tag above wrong? Type that word to fix it (Enter = no): ").strip().lower()
        if not word:
            break
        if not menu_shown:
            print_menu()
            menu_shown = True
        category = ask_category(word)
        if category:
            save_word(word, category)
            reload_lexicon()
            print("\n  Checking again:")
            accepted, tagged = show_result(sentence)

    topic = input("\n  Topic (Enter = %s): " % last_topic).strip() or last_topic
    sentence_id = save_sentence(topic, sentence)
    print("  Saved as sentence #%d." % sentence_id)
    return topic


def main():
    print("=" * 60)
    print("Yaoundé Language Analyzer - test and add sentences")
    print("=" * 60)
    print("Type a sentence and press Enter.  Type q to quit.")
    topic = "user_submitted"
    while True:
        try:
            sentence = input("\nSentence> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if sentence.lower() in ("q", "quit", "exit"):
            break
        if not sentence:
            continue
        try:
            topic = handle_sentence(sentence, topic)
        except (EOFError, KeyboardInterrupt):
            print("\n  (cancelled - this sentence was not saved)")
            break
    print("\nDone. Run  python parser\\parser.py  to see the updated totals.")


if __name__ == "__main__":
    main()
