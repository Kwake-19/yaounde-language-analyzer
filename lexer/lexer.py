"""
Yaoundé Language Analyzer - Lexical Analyzer
CS4110 Compiler Construction

Turns a raw sentence of informal, code-mixed Yaoundé speech (English, French,
Pidgin and Camfranglais slang) into a stream of (lexeme, CATEGORY) tokens.
These categories are the terminal symbols of the grammar in
grammar/grammar_notes.md.

Pipeline:
    1. lower-case, unify apostrophes
    2. split the text into raw words / numbers with a regex
    3. normalise spelling variants ("eske" -> "est-ce que")
    4. merge multi-word phrases into single tokens ("gare routiere")
    5. split French elisions ("j'ai" -> "j'" + "ai")
    6. tag each token (lexicon, then regex rules, then UNKNOWN)
    7. merge a number followed by a currency word ("500 frs")

Standard library only.
"""

import csv
import os
import re

# ---------------------------------------------------------------------------
# Token categories (terminals of the grammar)
# ---------------------------------------------------------------------------
NOUN = "NOUN"
VERB = "VERB"
PRONOUN = "PRONOUN"
PREPOSITION = "PREPOSITION"
ADJECTIVE = "ADJECTIVE"
GREETING_ADDRESS = "GREETING_ADDRESS"
DISCOURSE_MARKER = "DISCOURSE_MARKER"
TAG_QUESTION = "TAG_QUESTION"
SLANG_INTERJECTION = "SLANG_INTERJECTION"
MONEY_NUMBER = "MONEY_NUMBER"
LOCATION = "LOCATION"
PARTICLE = "PARTICLE"
UNKNOWN = "UNKNOWN"

# ---------------------------------------------------------------------------
# Spelling normalisation (applied to single raw words)
# ---------------------------------------------------------------------------
NORMALIZATION = {
    # French question / connector abbreviations
    "eske": "est-ce que", "esque": "est-ce que", "eskeu": "est-ce que",
    "estceque": "est-ce que", "est ce que": "est-ce que",
    "pk": "pourquoi", "pq": "pourquoi", "pkoi": "pourquoi", "pourkoi": "pourquoi",
    "pcq": "parce que", "psk": "parce que", "paske": "parce que",
    "koi": "quoi", "kwa": "quoi",
    "ke": "que", "k": "que",
    "c": "c'est", "cé": "c'est", "ces": "c'est", "sé": "c'est",
    "jsp": "je sais pas", "chui": "je suis", "chuis": "je suis",
    "tjrs": "toujours", "tjr": "toujours", "bcp": "beaucoup",
    "slt": "salut", "bjr": "bonjour", "bsr": "bonsoir", "cc": "salut",
    "stp": "s'il te plait", "svp": "s'il vous plait",
    "mr": "monsieur", "mme": "madame",
    # English / SMS spellings
    "u": "you", "ur": "your", "r": "are", "wat": "what", "wht": "what",
    "pls": "please", "plz": "please", "tnx": "thanks", "thx": "thanks",
    "gud": "good", "gd": "good", "bcos": "because", "bcoz": "because", "coz": "because",
    "dat": "that", "dis": "this", "d": "the", "n": "and", "2day": "today",
    "2moro": "tomorrow", "tmrw": "tomorrow",
    # Pidgin spelling variants
    "wetin": "wetin", "watin": "wetin", "weti": "wetin",
    "tori": "tory", "sabi": "sabi", "sabe": "sabi",
    "dem": "dem", "deh": "dey", "de": "de",
    "abeg": "abeg", "abeh": "abeg", "abegi": "abeg",
    "comot": "komot", "chop": "chop", "tchop": "chop",
    "bensikin": "bendskin", "bensiking": "bendskin", "benskin": "bendskin",
    "yde": "yaounde", "yaoundé": "yaounde",
    "gare-routiere": "gare routiere", "gare-routière": "gare routiere",
}

# ---------------------------------------------------------------------------
# Lexicon: category -> entries. Entries containing spaces are multi-word
# phrases and become a single token. Lookups are accent-insensitive.
# Earlier categories win if a word is listed twice.
# ---------------------------------------------------------------------------
LEXICON_SOURCE = [
    (TAG_QUESTION, [
        "abi", "non", "hein", "ehn", "enh", "ein", "n'est-ce pas", "no be so",
        "isn't it", "ou bien", "right", "quoi", "shey", "nor so",
    ]),
    (GREETING_ADDRESS, [
        "hello", "hi", "hey", "bonjour", "bonsoir", "salut", "good morning",
        "good afternoon", "good evening", "good night", "how now", "how far",
        "mon frere", "ma soeur", "mon gars", "my guy", "my brother", "my sister",
        "my dear", "ma cherie", "mon cheri", "bro", "sister", "sista", "broda",
        "mola", "massa", "mami", "mama", "papa", "tara", "chef", "boss", "patron",
        "gars", "mbom", "asso", "ndomo", "monsieur", "madame", "mademoiselle",
        "tonton", "tata", "grand", "le grand", "mon vieux", "please", "s'il te plait",
        "s'il vous plait", "thanks", "thank you", "merci", "bye", "ciao",
    ]),
    (DISCOURSE_MARKER, [
        "est-ce que", "parce que", "because", "but", "mais", "donc", "alors",
        "so", "and", "et", "or", "ou", "then", "after", "apres", "like", "comme",
        "quand", "when", "if", "si", "enfin", "bref", "en tout cas", "anyway",
        "actually", "vraiment", "really", "sinon", "even", "meme", "que", "qu'",
        "pourquoi", "why", "how", "comment", "since", "toujours", "encore",
        "deja", "just", "only", "seulement", "also", "aussi", "again", "maybe",
        "peut-etre", "voila", "tu vois", "you know", "i mean",
    ]),
    (SLANG_INTERJECTION, [
        "abeg", "eh", "ah", "oh", "o", "ooh", "eeh", "hmm", "walai", "wallah",
        "wallahi", "na wa", "chai", "ekie", "kai", "yeah", "yes", "yep", "oui",
        "nope", "no wahala", "no problem", "tchuip", "tchip", "mouf", "weh",
        "ashia", "sorry", "pardon", "eyeye", "hala", "nooo", "waka waka",
        "c'est comment", "on dit quoi", "ca va", "tout va bien", "okay", "ok",
        "bof", "zut", "merde", "wow", "lol", "mdr", "d'accord", "dacc",
    ]),
    (PRONOUN, [
        "i", "me", "my", "mine", "you", "your", "yours", "he", "him", "his",
        "she", "her", "hers", "it", "its", "we", "us", "our", "they", "them",
        "their", "myself", "yourself", "this", "that", "these", "those",
        "something", "nothing", "everything", "somebody", "nobody", "everybody",
        "who", "what", "which", "wetin", "whosai", "mi", "yi", "wuna", "dem",
        "ma", "ya", "je", "j'", "moi", "tu", "toi", "il", "elle", "on", "nous",
        "vous", "ils", "elles", "lui", "leur", "eux", "m'", "t'", "s'", "se",
        "te", "mon", "ton", "son", "mes", "tes", "ses", "notre", "votre",
        "nos", "vos", "ce", "ca", "cela", "ceci", "c'", "qui", "rien", "tout",
        "quelqu'un", "y",
    ]),
    (LOCATION, [
        "yaounde", "mvog-mbi", "mvog mbi", "mvog-ada", "mvog ada", "mokolo",
        "mfoundi", "mvan", "biyem-assi", "biyem assi", "bastos", "emana",
        "etoudi", "nkolbisson", "ngoa-ekelle", "ngoa ekelle", "essos", "obili",
        "mimboman", "nlongkak", "tsinga", "melen", "simbock", "odza", "ekounou",
        "nkoldongo", "elig-essono", "elig essono", "omnisport", "olezoa",
        "poste centrale", "carrefour", "carrefour warda", "warda", "rond point",
        "rond-point", "gare routiere", "gare voyageurs", "marche central",
        "marche mokolo", "mboa", "douala", "bamenda", "buea", "kribi",
        "bafoussam", "garoua", "town", "quartier", "kwat", "campus", "ictu",
        "uy1", "mboppi", "akwa", "home", "maison", "la maison", "village",
        "au village", "pays", "cameroun", "cameroon", "mbeng", "france",
        "church", "eglise", "hospital", "hopital", "stade", "stadium",
    ]),
    (VERB, [
        # multi-word verbs
        "drop me", "get down", "take care", "come back", "go back", "wait me",
        "tell me", "give me", "pick up", "no fit",
        "il y a", "y a", "i beg", "je sais pas",
        # English
        "come", "want", "wan", "like", "love", "need", "have", "has", "had",
        "be", "is", "am", "are", "was", "were", "do", "does", "did", "make",
        "get", "got", "give", "take", "buy", "sell", "pay", "see", "look",
        "know", "think", "say", "said", "talk", "tell", "call", "send", "bring",
        "carry", "eat", "drink", "sleep", "work", "reach", "find", "hear",
        "understand", "wait", "stop", "leave", "enter", "run", "play", "watch",
        "read", "write", "study", "learn", "live", "stay", "meet", "help",
        "try", "put", "open", "close", "start", "finish", "win", "lose",
        "can", "could", "will", "would", "should", "must", "fit", "cost",
        "drop", "pass", "move", "check", "use", "lend", "borrow", "owe",
        # Pidgin / Camfranglais
        "chop", "waka", "sabi", "tok", "kam", "komot", "gi", "lef", "shidon",
        "tcham", "nang", "ndjoss", "tchouk", "kick", "yamo", "tanap", "wash",
        "dash", "bolo", "nyang", "damer", "gerer", "gere", "tcheck", "cam",
        # French
        "c'est", "est", "suis", "es", "sommes", "etes", "sont", "etait",
        "ai", "as", "avons", "avez", "ont", "avoir", "etre", "faire", "fais",
        "fait", "faut", "dire", "dit", "dis", "veux", "veut", "voulez",
        "peux", "peut", "pouvez", "sais", "sait", "connais", "connait",
        "vais", "vas", "va", "allons", "allez", "vont", "aller", "viens",
        "vient", "venir", "venez", "mange", "manger", "mangé", "bois", "boire",
        "paie", "payer", "paye", "achete", "acheter", "vends", "vendre",
        "prends", "prend", "prendre", "donne", "donner", "parle", "parler",
        "pars", "part", "partir", "sors", "sortir", "mets", "mettre", "vois",
        "voir", "vu", "attends", "attendre", "cherche", "chercher", "trouve",
        "trouver", "appelle", "appeler", "dors", "dormir", "travaille",
        "travailler", "comprends", "comprendre", "aime", "aimer", "descends",
        "descendre", "depose", "deposer", "laisse", "laisser", "gagne",
        "gagner", "perdu", "envoie", "envoyer", "regarde", "regarder",
    ]),
    (ADJECTIVE, [
        "good", "bad", "fine", "big", "small", "sweet", "hot", "cold",
        "expensive", "cheap", "beautiful", "fine fine", "tired", "hungry",
        "happy", "sick", "tight", "correct", "long", "short", "far", "near",
        "late", "early", "ready", "serious", "hard", "easy", "plenty", "much",
        "many", "new", "old", "strong", "sure", "true", "free", "full",
        "busy", "clean", "dirty", "nice", "cool", "crazy", "mad", "broke",
        "mbout", "nyanga", "djim", "kick-kick", "wanda", "bad bad",
        "cher", "chere", "belle", "beau", "bon", "bonne", "mauvais", "petit",
        "petite", "gros", "grosse", "fatigue", "fatiguee", "malade", "content",
        "contente", "loin", "proche", "pret", "prete", "dur", "dure", "facile",
        "difficile", "grave", "chaud", "froid", "joli", "jolie", "nouveau",
        "vieux", "beaucoup", "trop", "too much", "tres", "very", "too",
        "propre", "sale", "fort", "vrai", "fou", "folle", "fauche",
    ]),
    (NOUN, [
        # transport / town life
        "taxi", "moto", "moto-taxi", "bendskin", "car", "bus", "agence",
        "driver", "chauffeur", "police", "mange-mille", "gendarme", "road",
        "route", "fare", "transport", "place", "embouteillage", "go-slow",
        # money / trade
        "money", "dough", "kolo", "doh", "argent", "monnaie", "change",
        "price", "prix", "credit", "data", "network", "reseau", "tchoko",
        "market", "marche", "boutique", "shop", "business", "njangi",
        # food / drink
        "food", "bread", "pain", "beer", "biere", "water", "eau", "ndole",
        "eru", "koki", "beignet", "beignets", "bouillie", "haricots", "soya",
        "poisson", "fish", "plantain", "plantains", "riz", "rice", "mbanga",
        "tapioca", "baton", "miondo", "sissongo", "jus", "top",
        # people
        "man", "woman", "pikin", "child", "children", "enfant", "nga", "ngo",
        "mbenguiste", "friend", "ami", "amie", "copain", "copine", "boy",
        "girl", "fille", "garcon", "wife", "husband", "femme", "mari",
        "people", "gens", "family", "famille", "mother", "father", "mere",
        "pere", "teacher", "prof", "student", "etudiant", "etudiante",
        "mbindi", "long crayon", "sauveteur", "bayam-sellam", "ashawo",
        # things / abstract
        "thing", "chose", "ting", "affaire", "problem", "probleme", "wahala",
        "palava", "kongossa", "tory", "story", "histoire", "news", "phone",
        "telephone", "tel", "house", "school", "ecole", "class", "classe",
        "exam", "examen", "cours", "work", "job", "boulot", "match", "ball",
        "foot", "music", "musique", "party", "fete", "day", "jour", "time",
        "temps", "today", "tomorrow", "yesterday", "now", "aujourd'hui",
        "demain", "hier", "maintenant", "morning", "night", "soir", "matin",
        "week", "semaine", "month", "mois", "year", "annee", "life",
        "vie", "god", "dieu", "name", "nom", "question", "way", "sun",
        "rain", "pluie", "light", "courant", "cadeau", "gift", "clothes",
        "habits", "shoes", "chaussures", "bag", "sac", "key", "cle",
    ]),
    (PREPOSITION, [
        "in", "on", "at", "for", "from", "to", "with", "about", "into",
        "inside", "under", "behind", "until", "till", "without", "near by",
        "a", "au", "aux", "de", "du", "des", "d'", "dans", "sur", "sous",
        "avec", "pour", "chez", "vers", "par", "sans", "depuis", "jusqu'a",
        "entre", "devant", "derriere", "pres de", "a cote de", "for inside",
    ]),
    (MONEY_NUMBER, [
        "frs", "fr", "francs", "franc", "fcfa", "cfa", "balles", "mille",
        "million", "millions", "dollars", "euros",
        "one", "two", "three", "four", "five", "ten", "hundred", "thousand",
        "deux", "trois", "quatre", "cinq", "dix", "cent",
    ]),
    (PARTICLE, [
        # Pidgin aspect / tense / negation / focus markers
        "don", "di", "dey", "na", "no", "go", "bin", "wey", "sef", "self",
        "so so", "don di",
        # French and English articles / negation clitics
        "le", "la", "les", "l'", "the", "an", "un", "une", "ne", "n'", "pas", "plus",
        "not", "don't", "dont", "doesn't", "didn't", "can't", "won't",
    ]),
]

CURRENCY_WORDS = {"frs", "fr", "francs", "franc", "fcfa", "cfa", "balles",
                  "mille", "million", "millions", "dollars", "euros", "k"}

# Regex rules ---------------------------------------------------------------
# Raw token splitter: numbers (with optional unit suffix) or words that may
# contain internal hyphens / apostrophes and may end in an elision apostrophe.
TOKEN_RE = re.compile(r"\d+(?:[.,]\d+)*[^\W\d_]*|[^\W\d_]+(?:[-'][^\W\d_]+)*'?")

# 500, 2.500, 1500frs, 5k, 10000fcfa
MONEY_RE = re.compile(r"^\d+(?:[.,]\d+)*(?:k|frs?|fcfa|cfa|f|balles|mille)?$")

# Any letter repeated 3+ times: "garrr", "ehhhh", "chaiiii", "noooo"
ELONGATED_RE = re.compile(r"([^\W\d_])\1{2,}")

# Shape of common interjections, even when not in the list: "ahhh", "hmmm",
# "eyyy", "ekieee", "tchuiiip"
INTERJECTION_SHAPE_RE = re.compile(
    r"^(?:a+h*|e+h+|o+h+|h+m+|e+y+|e+k+i+e+|c+h+a+i+|k+a+i+|y+e+|w+e+h*|"
    r"t+c+h+u+i+p+s*|a+i+e+|h+a+)$"
)

# French elisions: j'ai, l'argent, n'est, d'accord, qu'il, m'a, t'es, s'il
ELISION_RE = re.compile(r"^(j|l|n|d|m|t|s|c|qu)'(.+)$")

_ACCENTS = str.maketrans("àâäáéèêëíîïóôöòúùûüçñ", "aaaaeeeeiiioooouuuucn")


def strip_accents(text):
    return text.translate(_ACCENTS)


def _build_lexicon():
    words, phrases = {}, {}
    for category, entries in LEXICON_SOURCE:
        for entry in entries:
            key = strip_accents(entry.lower())
            if " " in key:
                phrases.setdefault(tuple(key.split()), category)
            else:
                words.setdefault(key, category)
    return words, phrases


WORDS, PHRASES = _build_lexicon()
MAX_PHRASE_LEN = max(len(p) for p in PHRASES)


# ---------------------------------------------------------------------------
# Tokenizing
# ---------------------------------------------------------------------------
def _raw_words(sentence):
    text = sentence.lower().replace("’", "'").replace("`", "'")
    return TOKEN_RE.findall(text)


def _normalize(words):
    out = []
    for w in words:
        replacement = NORMALIZATION.get(w, NORMALIZATION.get(strip_accents(w), w))
        out.extend(replacement.split())
    return out


def _split_elisions(words):
    out = []
    for w in words:
        m = ELISION_RE.match(w)
        if m and " " not in w and strip_accents(w) not in WORDS:
            out.extend([m.group(1) + "'", m.group(2)])
        else:
            out.append(w)
    return out


def _merge_phrases(words):
    """Greedy longest-match merging of multi-word lexicon phrases."""
    out, i = [], 0
    keys = [strip_accents(w) for w in words]
    while i < len(words):
        for n in range(min(MAX_PHRASE_LEN, len(words) - i), 1, -1):
            if tuple(keys[i:i + n]) in PHRASES:
                out.append(" ".join(words[i:i + n]))
                i += n
                break
        else:
            out.append(words[i])
            i += 1
    return out


def tokenize(sentence):
    """Split a sentence into normalised tokens (multi-word phrases kept whole)."""
    words = _raw_words(sentence)
    words = _normalize(words)
    words = _merge_phrases(words)
    return _split_elisions(words)


# ---------------------------------------------------------------------------
# Tagging
# ---------------------------------------------------------------------------
def tag_token(token):
    key = strip_accents(token)

    if " " in key:
        return PHRASES.get(tuple(key.split()), UNKNOWN)
    if key in WORDS:
        return WORDS[key]
    if MONEY_RE.match(key):
        return MONEY_NUMBER

    # Elongated spelling ("garrr", "noooo"): collapse the repeated letters and
    # retry the lexicon; if still unknown, the stretched spelling itself marks
    # it as expressive slang.
    if ELONGATED_RE.search(key):
        for collapsed in (ELONGATED_RE.sub(r"\1", key), ELONGATED_RE.sub(r"\1\1", key)):
            if collapsed in WORDS:
                return WORDS[collapsed]
        return SLANG_INTERJECTION
    if INTERJECTION_SHAPE_RE.match(key):
        return SLANG_INTERJECTION
    return UNKNOWN


def _merge_money(tagged):
    """'500' + 'frs' -> '500 frs' as one MONEY_NUMBER token."""
    out = []
    for token, tag in tagged:
        if (out and out[-1][1] == MONEY_NUMBER and tag == MONEY_NUMBER
                and strip_accents(token) in CURRENCY_WORDS):
            out[-1] = (out[-1][0] + " " + token, MONEY_NUMBER)
        else:
            out.append((token, tag))
    return out


def analyze_sentence(sentence):
    """Return a list of (lexeme, CATEGORY) pairs for one sentence."""
    return _merge_money([(tok, tag_token(tok)) for tok in tokenize(sentence)])


# ---------------------------------------------------------------------------
# Dataset helpers
# ---------------------------------------------------------------------------
DEFAULT_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "..", "data", "collected_sentences.csv")

# Used only when the dataset has no rows yet, so the scripts can be smoke-tested.
# These are NOT part of the collected corpus.
DEMO_SENTENCES = [
    "Mola, drop me for gare routiere abeg",
    "Eske tu as le kolo?",
    "My guy the taxi don take 500 frs, na wa o",
    "I di come, wait me for Mvog-Mbi",
    "Garrr, dis ndole sweet eh",
    "Ma soeur, on dit quoi?",
    "Je vais au marche, abi?",
    "Wuna don see the mbindi for campus?",
]


def load_sentences(path=DEFAULT_CSV):
    """Read (id, topic, sentence) rows; skips rows with an empty sentence."""
    rows = []
    if not os.path.exists(path):
        print("Warning: dataset not found at %s" % os.path.normpath(path))
        return rows
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            sentence = (row.get("sentence") or "").strip()
            if sentence:
                rows.append({"id": (row.get("id") or "").strip(),
                             "topic": (row.get("topic") or "").strip(),
                             "sentence": sentence})
    return rows


def demo_rows():
    return [{"id": "demo%d" % (i + 1), "topic": "demo", "sentence": s}
            for i, s in enumerate(DEMO_SENTENCES)]


if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")

    rows = load_sentences()
    if rows:
        print("Loaded %d sentences from %s\n" % (len(rows), os.path.normpath(DEFAULT_CSV)))
    else:
        print("Dataset is empty - using built-in demo sentences (not part of the corpus).\n")
        rows = demo_rows()

    for row in rows[:8]:
        print("[%s] %s" % (row["id"], row["sentence"]))
        for token, tag in analyze_sentence(row["sentence"]):
            print("    %-22s %s" % (token, tag))
        print()
