"""
build_dictionary.py  (one-off tool - you do NOT need to run this again)

Builds data/dictionary.csv: a general English + French vocabulary where every
word already has one of the analyzer's categories. The lexer uses it as a
LOW-PRIORITY fallback: your own lexicon and data/vocabulary.csv always win.

Sources (cite these in the report):
  * Princeton WordNet (via NLTK)       - English words + part of speech
  * spaCy lookups data (French tables) - French words/verb forms + part of speech
                                          (derived from the Lefff lexicon)
  * wordfreq                           - which words are common (keeps the file small)
  * small hand-written lists below     - function words (of, by, dans, avec ...)
                                          that dictionaries do not contain

How a category is chosen for a word:
  1. hand-written function-word lists win
  2. otherwise the word's most frequent part of speech is used
     (WordNet sense counts for English, lemma frequency for French)
  3. a word found in both languages keeps the more frequent language's reading

Requires: pip install nltk wordfreq spacy-lookups-data
"""

import csv
import gzip
import json
import re
from pathlib import Path

import nltk
from nltk.corpus import wordnet as wn
from wordfreq import top_n_list, zipf_frequency

TOP_N = 50000  # most frequent words to consider per language
OUT = Path(__file__).resolve().parent.parent / "data" / "dictionary.csv"

_ACCENTS = str.maketrans("àâäáéèêëíîïóôöòúùûüçñ", "aaaaeeeeiiioooouuuucn")
WORD_RE = re.compile(r"^[a-zàâäáéèêëíîïóôöòúùûüçñœæ]+(?:-[a-zàâäáéèêëíîïóôöòúùûüçñœæ]+)*$")


def strip_accents(s):
    return s.translate(_ACCENTS)


# ---------------------------------------------------------------- function words
FUNCTION_WORDS = {
    # English
    "PREPOSITION": ("of by up out off over before after between through during against "
                    "among around across along toward towards upon within beyond above below "
                    "beside besides despite except outside onto per via amid beneath underneath "
                    # French
                    "a dans sur sous avec sans pour par chez entre vers depuis pendant avant "
                    "apres devant derriere contre selon malgre parmi envers jusque durant hors "
                    "outre via"),
    "DISCOURSE_MARKER": ("nor yet though although unless while whether once whereas therefore "
                         "however thus hence otherwise meanwhile moreover instead "
                         "et ou mais donc car ni lorsque puisque quoique pourtant cependant "
                         "ainsi puis ensuite sinon toutefois"),
    "PARTICLE": ("a an the some any every each all both another several few either neither "
                 "le la les un une des du au aux cet cette ces quelques plusieurs chaque "
                 "certains certaines aucun aucune"),
    "PRONOUN": ("someone anyone everyone anybody anything one ones whom whose whatever whoever "
                "whichever itself himself herself themselves ourselves yourselves here "
                "je tu il elle on nous vous ils elles me te se lui leur eux moi toi soi y en "
                "ce ca cela ceci qui quoi dont celui celle ceux celles chacun chacune "
                "rien tout mon ton son ma ta sa mes tes ses notre votre nos vos leurs"),
    "ADJECTIVE": "more most less least other such same own enough whole half",
    "VERB": "may might shall ought",
    "MONEY_NUMBER": ("six seven eight nine eleven twelve thirteen fourteen fifteen sixteen "
                     "seventeen eighteen nineteen twenty thirty forty fifty sixty seventy "
                     "eighty ninety zero "
                     "zero six sept huit neuf onze douze treize quatorze quinze seize vingt "
                     "trente quarante cinquante soixante"),
}


# ---------------------------------------------------------------- French tables
def load_fr(name):
    import spacy_lookups_data
    p = Path(spacy_lookups_data.__file__).parent / "data" / (name + ".json.gz")
    with gzip.open(p, "rt", encoding="utf-8") as f:
        return json.load(f)


def main():
    nltk.download("wordnet", quiet=True)
    fr_idx = {k: set(v) for k, v in load_fr("fr_lemma_index").items()}
    fr_exc = load_fr("fr_lemma_exc")
    fr_lookup = load_fr("fr_lemma_lookup")
    # the index lists miss many lemmas (e.g. most verb infinitives); every lemma that
    # appears in the inflection tables is also a real lemma of that part of speech
    for pos, table in fr_exc.items():
        for lemmas in table.values():
            fr_idx.setdefault(pos, set()).update(lemmas)

    # best[key] = (priority, zipf, category, language)
    best = {}

    def offer(word, category, priority, zipf, lang):
        key = strip_accents(word.lower())
        cur = best.get(key)
        if cur is None or (priority, zipf) > (cur[0], cur[1]):
            best[key] = (priority, zipf, category, lang)

    # 1. hand-written function words (highest priority)
    for category, words in FUNCTION_WORDS.items():
        for w in words.split():
            offer(w, category, 3, 9.0, "fn")

    # 2. English (WordNet)
    wn_map = (("n", "NOUN"), ("v", "VERB"), ("a", "ADJECTIVE"), ("r", "DISCOURSE_MARKER"))

    def wn_score(lemma, pos):
        total = 0
        for syn in wn.synsets(lemma, pos=pos):
            for l in syn.lemmas():
                if l.name().lower() == lemma:
                    total += l.count()
        return total

    for w in top_n_list("en", TOP_N):
        if len(w) < 2 or not WORD_RE.match(w):
            continue
        cands = []
        for order, (pos, cat) in enumerate(wn_map):
            lemma = wn.morphy(w, pos)
            if lemma:
                cands.append((wn_score(lemma, pos), -order, cat))
        if cands:
            _, _, cat = max(cands)
            offer(w, cat, 1, zipf_frequency(w, "en"), "en")

    # 3. French (spaCy tables)
    fr_map = (("noun", "NOUN"), ("verb", "VERB"), ("adj", "ADJECTIVE"), ("adv", "DISCOURSE_MARKER"))
    for w in top_n_list("fr", TOP_N):
        if len(w) < 2 or not WORD_RE.match(w):
            continue
        if w in fr_exc.get("aux", {}):
            offer(w, "VERB", 2, zipf_frequency(w, "fr"), "fr")
            continue
        cands = []
        for order, (pos, cat) in enumerate(fr_map):
            # "strong" evidence: the word is listed as an inflected form of this part of speech
            strong = set(fr_exc.get(pos, {}).get(w, []))
            weak = set()
            if w in fr_idx.get(pos, ()):
                weak.add(w)
            for l in fr_lookup.get(w, []):
                if l in fr_idx.get(pos, ()):
                    weak.add(l)
            for l in strong | weak:
                zl = zipf_frequency(l, "fr")
                if l != w and zl + 1.5 < zipf_frequency(w, "fr"):
                    continue  # word is far more common than its supposed lemma: unreliable
                cands.append((zl + (1.0 if l in strong else 0.0), -order, cat))
        if cands:
            _, _, cat = max(cands)
            offer(w, cat, 1, zipf_frequency(w, "fr"), "fr")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["word", "category", "source"])
        for key in sorted(best):
            _, _, cat, lang = best[key]
            writer.writerow([key, cat, lang])
    print("Wrote %d words to %s" % (len(best), OUT))


if __name__ == "__main__":
    main()
