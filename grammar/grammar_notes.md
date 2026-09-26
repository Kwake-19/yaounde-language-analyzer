# Grammar Notes: Yaoundé Code-Mixed Speech

CS4110 Compiler Construction, Yaoundé Language Analyzer

This file defines the context-free grammar (CFG) that the parser in
`parser/parser.py` recognises. It then transforms the grammar into LL(1) form
and builds the predictive parsing table.

## Terminals

The terminals are the token categories produced by `lexer/lexer.py`:

| Terminal | Short | Examples |
|---|---|---|
| `NOUN` | n | taxi, kolo, ndole, wahala, mbindi |
| `VERB` | v | chop, waka, drop me, vais, c'est |
| `PRONOUN` | pro | i, mi, wuna, je, tu, ça |
| `PREPOSITION` | prep | for, to, au, dans, chez |
| `ADJECTIVE` | adj | sweet, mbout, cher, fatigué |
| `GREETING_ADDRESS` | greet | mola, my guy, ma soeur, bonjour |
| `DISCOURSE_MARKER` | disc | est-ce que, but, donc, parce que |
| `TAG_QUESTION` | tag | abi, non, hein, no be so |
| `SLANG_INTERJECTION` | slang | abeg, na wa, chai, garrr |
| `MONEY_NUMBER` | money | 500, 2k, 5000frs, 500 frs |
| `LOCATION` | loc | Mvog-Mbi, gare routiere, Mokolo |
| `$` | $ | end of input |

`PARTICLE` tokens (Pidgin `don/di/dey/na/no/go`, articles `le/la/the`,
negation `ne/pas`) are **not** terminals of the grammar. They carry
tense/aspect/negation/determiner information but do not change the phrase
structure, so the parser removes them before parsing. `UNKNOWN` tokens are not
terminals either, and any sentence that contains one is rejected before
parsing.

---

## 1. Original CFG

Non-terminals start with a capital letter and terminals are in `UPPER_CASE`.
`S` is the start symbol.

```
S       → Pre Core
Pre     → Marker Pre | ε
Marker  → GREETING_ADDRESS | DISCOURSE_MARKER | SLANG_INTERJECTION
Core    → Clause Post | TAG_QUESTION S | ε
Post    → Marker S | TAG_QUESTION S | ε
Clause  → NP Pred | VP | PP Clause
Pred    → VP | ε
NP      → NP ADJECTIVE | Head                      ← deliberately LEFT-RECURSIVE
Head    → NOUN | PRONOUN | LOCATION | MONEY_NUMBER
VP      → VERB ADJECTIVE Comps | VERB Comps        ← deliberately COMMON PREFIX
Comps   → Comp Comps | VP | ε
Comp    → NP | PP
PP      → PREPOSITION NP
```

What each rule models:

* **S / Pre / Core / Post**: an utterance is a run of address forms, greetings,
  discourse markers and interjections (`Mola, abeg, ...`), then at most one
  clause, then optionally a tag question or another marker. After that marker
  a whole new utterance `S` may follow. This covers chained speech such as
  `Mola, i di come, abi? we go chop`.
* **Clause**: a subject noun phrase with an optional predicate
  (`dis ndole sweet`, `i di come`), a subject-less verb phrase
  (`drop me for gare routiere`), or a fronted prepositional phrase
  (`for campus, i see am`).
* **NP → NP ADJECTIVE**: adjectives follow the noun in Pidgin and French
  (`ndole sweet`, `taxi cher`, `gars mbout`), and they can stack
  (`ndole sweet hot`). This is the natural rule to write, and it is left-recursive.
* **VP**: a verb optionally followed by a predicative adjective
  (`c'est bon`, `i be tired`), then any number of complements (objects, PPs)
  or a chained serial verb (`come chop`, `vais manger`).

---

## 2. Left Recursion Removal

The rule `NP → NP ADJECTIVE | Head` has the form `A → A α | β` with
`α = ADJECTIVE` and `β = Head`. A top-down parser expanding `NP` on the input
would expand `NP` again without consuming a token and would never stop.

We use the standard transformation `A → β A'`, `A' → α A' | ε`:

```
NP   → NP ADJECTIVE | Head
```
becomes
```
NP   → Head NP'
NP'  → ADJECTIVE NP' | ε
```

Both grammars generate `Head ADJECTIVE*`. The new grammar is right-recursive,
so every expansion of `NP'` consumes an `ADJECTIVE` or ends. No other rule is
left-recursive, directly or indirectly: every other right-hand side starts with
a terminal or with a non-terminal (`Pre`, `Marker`, `Clause`, `NP`, `Head`,
`VP`, `Comp`, `PP`) that cannot derive a string beginning with the rule's own
left-hand side.

---

## 3. Left Factoring

The rule `VP → VERB ADJECTIVE Comps | VERB Comps` has two alternatives that
share the prefix `VERB`. With one token of lookahead (`VERB`) the parser cannot
choose between them.

We use the standard transformation `A → α β1 | α β2` becomes `A → α A'`,
`A' → β1 | β2`:

```
VP   → VERB ADJECTIVE Comps | VERB Comps
```
becomes
```
VP   → VERB VP'
VP'  → ADJECTIVE Comps | Comps
```

No other non-terminal has two alternatives that start with the same symbol.

### Final (LL(1)) grammar, numbered

These numbers are used in the parsing table and in `parser.py`.

| # | Production |
|---|---|
| 1 | S → Pre Core |
| 2 | Pre → Marker Pre |
| 3 | Pre → ε |
| 4 | Marker → GREETING_ADDRESS |
| 5 | Marker → DISCOURSE_MARKER |
| 6 | Marker → SLANG_INTERJECTION |
| 7 | Core → Clause Post |
| 8 | Core → TAG_QUESTION S |
| 9 | Core → ε |
| 10 | Post → Marker S |
| 11 | Post → TAG_QUESTION S |
| 12 | Post → ε |
| 13 | Clause → NP Pred |
| 14 | Clause → VP |
| 15 | Clause → PP Clause |
| 16 | Pred → VP |
| 17 | Pred → ε |
| 18 | NP → Head NP' |
| 19 | NP' → ADJECTIVE NP' |
| 20 | NP' → ε |
| 21 | Head → NOUN |
| 22 | Head → PRONOUN |
| 23 | Head → LOCATION |
| 24 | Head → MONEY_NUMBER |
| 25 | VP → VERB VP' |
| 26 | VP' → ADJECTIVE Comps |
| 27 | VP' → Comps |
| 28 | Comps → Comp Comps |
| 29 | Comps → VP |
| 30 | Comps → ε |
| 31 | Comp → NP |
| 32 | Comp → PP |
| 33 | PP → PREPOSITION NP |

---

## 4. FIRST Sets

Nullable non-terminals: `S, Pre, Core, Post, Pred, NP', VP', Comps`.

For readability let **H** = { NOUN, PRONOUN, LOCATION, MONEY_NUMBER }
(the terminals that can start a noun phrase).

| Non-terminal | FIRST |
|---|---|
| Head | { NOUN, PRONOUN, LOCATION, MONEY_NUMBER } = H |
| NP | H |
| NP' | { ADJECTIVE, ε } |
| PP | { PREPOSITION } |
| Comp | H ∪ { PREPOSITION } |
| VP | { VERB } |
| Comps | H ∪ { PREPOSITION, VERB, ε } |
| VP' | H ∪ { ADJECTIVE, PREPOSITION, VERB, ε } |
| Pred | { VERB, ε } |
| Clause | H ∪ { VERB, PREPOSITION } |
| Marker | { GREETING_ADDRESS, DISCOURSE_MARKER, SLANG_INTERJECTION } |
| Pre | { GREETING_ADDRESS, DISCOURSE_MARKER, SLANG_INTERJECTION, ε } |
| Post | { GREETING_ADDRESS, DISCOURSE_MARKER, SLANG_INTERJECTION, TAG_QUESTION, ε } |
| Core | H ∪ { VERB, PREPOSITION, TAG_QUESTION, ε } |
| S | H ∪ { VERB, PREPOSITION, TAG_QUESTION, GREETING_ADDRESS, DISCOURSE_MARKER, SLANG_INTERJECTION, ε } |

How some of these follow from the productions:

* `FIRST(Clause) = FIRST(NP) ∪ FIRST(VP) ∪ FIRST(PP)`, from rules 13, 14 and 15.
* `FIRST(Comps) = FIRST(Comp) ∪ FIRST(VP) ∪ {ε}`, from rules 28, 29 and 30.
* `FIRST(S)`: `Pre` is nullable, so `FIRST(S) = FIRST(Pre) ∪ FIRST(Core)`. Both
  contain ε, so `S` is nullable too.

---

## 5. FOLLOW Sets

Let **C** = { GREETING_ADDRESS, DISCOURSE_MARKER, SLANG_INTERJECTION,
TAG_QUESTION, $ } (the tokens that may follow a complete clause).

| Non-terminal | FOLLOW |
|---|---|
| S | { $ } |
| Core | { $ } |
| Post | { $ } |
| Pre | H ∪ { VERB, PREPOSITION, TAG_QUESTION, $ } |
| Marker | H ∪ { VERB, PREPOSITION, TAG_QUESTION, GREETING_ADDRESS, DISCOURSE_MARKER, SLANG_INTERJECTION, $ } |
| Clause | C |
| Pred | C |
| VP | C |
| VP' | C |
| Comps | C |
| Comp | H ∪ { PREPOSITION, VERB } ∪ C |
| PP | H ∪ { PREPOSITION, VERB } ∪ C |
| NP | H ∪ { PREPOSITION, VERB } ∪ C |
| NP' | H ∪ { PREPOSITION, VERB } ∪ C |
| Head | H ∪ { ADJECTIVE, PREPOSITION, VERB } ∪ C |

Derivation:

* `FOLLOW(S)`: `$` because `S` is the start symbol. `S` also appears at the end
  of rules 8, 10 and 11, which adds `FOLLOW(Core)` and `FOLLOW(Post)`. Those two
  sets are themselves equal to `FOLLOW(S)`, so the result is `{ $ }`.
* `FOLLOW(Pre)`: rule 1 gives `FIRST(Core) − ε` plus `FOLLOW(S)`, because
  `Core` is nullable.
* `FOLLOW(Marker)`: rule 2 gives `FIRST(Pre) − ε ∪ FOLLOW(Pre)`. Rule 10 adds
  `FIRST(S) − ε ∪ FOLLOW(Post)`.
* `FOLLOW(Clause)`: rule 7 gives `FIRST(Post) − ε ∪ FOLLOW(Core)` = C. Rule 15
  only adds `FOLLOW(Clause)` to itself.
* `FOLLOW(Pred) = FOLLOW(Clause)` from rule 13.
* `FOLLOW(VP)`: `VP` ends rules 14, 16 and 29, and `VP'` ends rule 25. The
  result is `FOLLOW(Clause) ∪ FOLLOW(Pred) ∪ FOLLOW(Comps)` = C.
* `FOLLOW(VP') = FOLLOW(VP)` and `FOLLOW(Comps) = FOLLOW(VP')`, from rules 25,
  26, 27 and 28. Both equal C.
* `FOLLOW(Comp)`: rule 28 gives `FIRST(Comps) − ε ∪ FOLLOW(Comps)`.
* `FOLLOW(PP)`: rule 32 adds `FOLLOW(Comp)` and rule 15 adds `FIRST(Clause)`.
* `FOLLOW(NP)`: rule 13 gives `FIRST(Pred) − ε ∪ FOLLOW(Clause)`, rule 31 gives
  `FOLLOW(Comp)` and rule 33 gives `FOLLOW(PP)`.
* `FOLLOW(NP') = FOLLOW(NP)` from rules 18 and 19.
* `FOLLOW(Head)`: rule 18 gives `FIRST(NP') − ε ∪ FOLLOW(NP)`, since `NP'` is
  nullable.

---

## 6. LL(1) Parsing Table

Entry `M[A, a]` gives the number of the production to apply when `A` is on
top of the stack and `a` is the next input token. The construction rule is:
for each production `A → α`, put it in `M[A, a]` for every `a ∈ FIRST(α)`. If
`α` is nullable, also put it in `M[A, b]` for every `b ∈ FOLLOW(A)`. Blank
cells are syntax errors.

Column abbreviations: n = NOUN, pro = PRONOUN, loc = LOCATION,
money = MONEY_NUMBER, v = VERB, adj = ADJECTIVE, prep = PREPOSITION,
greet = GREETING_ADDRESS, disc = DISCOURSE_MARKER, slang = SLANG_INTERJECTION,
tag = TAG_QUESTION.

| | n | pro | loc | money | v | adj | prep | greet | disc | slang | tag | $ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **S** | 1 | 1 | 1 | 1 | 1 | | 1 | 1 | 1 | 1 | 1 | 1 |
| **Pre** | 3 | 3 | 3 | 3 | 3 | | 3 | 2 | 2 | 2 | 3 | 3 |
| **Marker** | | | | | | | | 4 | 5 | 6 | | |
| **Core** | 7 | 7 | 7 | 7 | 7 | | 7 | | | | 8 | 9 |
| **Post** | | | | | | | | 10 | 10 | 10 | 11 | 12 |
| **Clause** | 13 | 13 | 13 | 13 | 14 | | 15 | | | | | |
| **Pred** | | | | | 16 | | | 17 | 17 | 17 | 17 | 17 |
| **NP** | 18 | 18 | 18 | 18 | | | | | | | | |
| **NP'** | 20 | 20 | 20 | 20 | 20 | 19 | 20 | 20 | 20 | 20 | 20 | 20 |
| **Head** | 21 | 22 | 23 | 24 | | | | | | | | |
| **VP** | | | | | 25 | | | | | | | |
| **VP'** | 27 | 27 | 27 | 27 | 27 | 26 | 27 | 27 | 27 | 27 | 27 | 27 |
| **Comps** | 28 | 28 | 28 | 28 | 29 | | 28 | 30 | 30 | 30 | 30 | 30 |
| **Comp** | 31 | 31 | 31 | 31 | | | 32 | | | | | |
| **PP** | | | | | | | 33 | | | | | |

---

## 7. Conflict Check

The grammar is LL(1) if and only if no cell holds more than one production.
That is the case when, for every non-terminal `A` with alternatives
`A → α | β`:

1. `FIRST(α) ∩ FIRST(β) = ∅`, and
2. if `β` is nullable, `FIRST(α) ∩ FOLLOW(A) = ∅`.

Checking every non-terminal that has more than one alternative:

| Non-terminal | Alternatives: FIRST sets | Nullable alt: FOLLOW(A) | Disjoint? |
|---|---|---|---|
| Pre | {greet, disc, slang} | ε: H ∪ {v, prep, tag, $} | ✔ |
| Marker | {greet} / {disc} / {slang} | none | ✔ |
| Core | H ∪ {v, prep} / {tag} | ε: {$} | ✔ |
| Post | {greet, disc, slang} / {tag} | ε: {$} | ✔ |
| Clause | H / {v} / {prep} | none | ✔ |
| Pred | {v} | ε: C | ✔ (v ∉ C) |
| NP' | {adj} | ε: H ∪ {prep, v} ∪ C | ✔ (adj ∉ FOLLOW) |
| Head | {n} / {pro} / {loc} / {money} | none | ✔ |
| VP' | {adj} / H ∪ {prep, v} | Comps alt is nullable: C | ✔ |
| Comps | H ∪ {prep} / {v} | ε: C | ✔ |
| Comp | H / {prep} | none | ✔ |

**Every cell of the table contains at most one production, so there are no
conflicts and the grammar is LL(1).**

Two points in the design matter for this result:

* `ADJECTIVE` is not allowed to start a complement (`Comp`). If it were,
  `ADJECTIVE` would be in `FOLLOW(NP')` and would clash with
  `NP' → ADJECTIVE NP'`. Predicative adjectives are therefore attached directly
  after the verb (`VP' → ADJECTIVE Comps`).
* Markers inside an utterance are only accepted **after** a clause (`Post`).
  They are never accepted as an optional prefix of `Clause`. This keeps
  `FOLLOW(Pre)` free of marker tokens.

`parser.py` checks this automatically. When it runs, it recomputes FIRST,
FOLLOW and the table from the grammar and compares the result with the
hand-built table above.

---

## Known Limitations

These are deliberate simplifications of a real grammar of Yaoundé speech:

* Compound nouns and bare noun sequences (`taxi driver`) are rejected unless
  the lexicon lists them as one multi-word token. Allowing `Head Head` would
  put `H` in `FIRST(NP')` and clash with objects in `Comps`.
* Two clauses joined without a marker are only accepted when the second clause
  starts with a verb (serial-verb reading through `Comps → VP`).
* Words the lexer tags as `UNKNOWN` cause immediate rejection. The fix is to
  extend the lexicon, not the grammar.
