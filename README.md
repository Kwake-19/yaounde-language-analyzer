# Yaoundé Language Analyzer

A CS4110 (Compiler Construction) group project. It builds the **front end of a
compiler** (a lexical analyzer and an LL(1) predictive parser) for informal,
code-mixed speech from Yaoundé, Cameroon. This speech mixes English, French,
Cameroonian Pidgin and Camfranglais slang ("franc-anglais").

```
"Mola, drop me for gare routiere abeg"
   │
   ▼  lexer/lexer.py
mola/GREETING_ADDRESS  drop me/VERB  for/PREPOSITION  gare routiere/LOCATION  abeg/SLANG_INTERJECTION
   │
   ▼  parser/parser.py  (LL(1) table + stack)
ACCEPTED
```

## What It Does

**Lexer (`lexer/lexer.py`)**

* Normalises spelling variants, for example `eske` becomes `est-ce que`,
  `pcq` becomes `parce que` and `u` becomes `you`.
* Splits French elisions, for example `j'ai` becomes `j'` + `ai`.
* Keeps multi-word phrases as a single token, for example `drop me`,
  `gare routiere` and `na wa`.
* Tags every token with one of these categories: NOUN, VERB, PRONOUN,
  PREPOSITION, ADJECTIVE, GREETING_ADDRESS, DISCOURSE_MARKER, TAG_QUESTION,
  SLANG_INTERJECTION, MONEY_NUMBER, LOCATION, PARTICLE or UNKNOWN.
* Uses regular expressions for open-ended classes:
  * amounts of money: `500`, `2k`, `5000frs`, `500 frs`
  * stretched spellings: `garrr`, `chaiii`
  * interjection shapes: `ahhh`, `hmmm`

**Grammar (`grammar/grammar_notes.md`)**

* A CFG whose terminals are the lexer's categories.
* Left recursion is removed and the grammar is left-factored.
* Includes the FIRST and FOLLOW sets, the full LL(1) parse table and a check
  that the table has no conflicts.

**Parser (`parser/parser.py`)**

* A table-driven, stack-based LL(1) predictive parser.
* It rejects sentences that contain UNKNOWN tokens and skips PARTICLE tokens
  (`don`, `di`, `dey`, `na`, `le`, `la`, and so on).
* It prints Accepted/Rejected counts for the whole dataset and a sample
  results table.
* It prints a full parse trace for one example sentence.
* On every run it recomputes FIRST, FOLLOW and the parse table from the grammar
  and checks them against the hand-built table.

Only the Python standard library is used. Nothing needs to be installed.

## Running Locally

You need Python 3.8 or newer.

```bash
# Tag sentences with the lexer
cd lexer
python lexer.py

# Parse the whole dataset
cd ../parser
python parser.py

# Parse a single sentence and show its full LL(1) trace
python parser.py "Je vais au marche, abi?"
```

On some systems the command is `python3` instead of `python`.

If `data/collected_sentences.csv` has no rows yet, both scripts run on a few
built-in demo sentences. These demo sentences are not part of the corpus.

## Running with Docker

```bash
docker build -t yaounde-analyzer .
docker run --rm yaounde-analyzer
```

To parse a single sentence:

```bash
docker run --rm yaounde-analyzer python3 parser.py "Mola, drop me for Mokolo"
```

Rebuild the image after you edit the dataset, because the data is copied into
the image at build time.

## Dataset Format

`data/collected_sentences.csv` has three columns:

| column | meaning |
|---|---|
| `id` | unique sentence id |
| `topic` | context of the conversation (transport, market, school, ...) |
| `sentence` | the sentence exactly as it was heard or written |

Save the file as UTF-8. Wrap a sentence in double quotes if it contains a comma.

## Folder Structure

```
yaounde-language-analyzer/
├── .gitignore
├── .dockerignore
├── Dockerfile               # python:3.11-slim image that runs the parser
├── README.md
├── data/
│   └── collected_sentences.csv   # the collected corpus (id, topic, sentence)
├── lexer/
│   └── lexer.py             # lexical analyzer: normalise, tokenize, tag
├── grammar/
│   └── grammar_notes.md     # CFG, transformations, FIRST/FOLLOW, LL(1) table
├── parser/
│   └── parser.py            # LL(1) predictive parser + dataset runner
├── report/
│   └── README.md            # final written report (placeholder)
└── slides/
    └── README.md            # final presentation (placeholder)
```
