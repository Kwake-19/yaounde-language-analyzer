"""
Yaoundé Language Analyzer - LL(1) Predictive Parser
CS4110 Compiler Construction

A table-driven, stack-based LL(1) parser for the grammar documented in
grammar/grammar_notes.md. Tokens come from lexer/lexer.py.

Usage (from the project root; "python parser.py" from inside parser/ also works):
    python parser/parser.py                   run the whole dataset
    python parser/parser.py "some sentence"   parse one sentence and print its trace

Standard library only.
"""

import sys
from pathlib import Path

# lexer.py lives in the sibling lexer/ folder (not a package), so put that
# folder on the import path. Built from __file__, so the import works no
# matter which directory the script is started from.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "lexer"))

import lexer  # noqa: E402

EPSILON = "ε"
END = "$"
START = "S"

# ---------------------------------------------------------------------------
# Grammar (final LL(1) form, numbered exactly as in grammar_notes.md)
# ---------------------------------------------------------------------------
GRAMMAR = {
    1: ("S", ["Pre", "Core"]),
    2: ("Pre", ["Marker", "Pre"]),
    3: ("Pre", []),
    4: ("Marker", ["GREETING_ADDRESS"]),
    5: ("Marker", ["DISCOURSE_MARKER"]),
    6: ("Marker", ["SLANG_INTERJECTION"]),
    7: ("Core", ["Clause", "Post"]),
    8: ("Core", ["TAG_QUESTION", "S"]),
    9: ("Core", []),
    10: ("Post", ["Marker", "S"]),
    11: ("Post", ["TAG_QUESTION", "S"]),
    12: ("Post", []),
    13: ("Clause", ["NP", "Pred"]),
    14: ("Clause", ["VP"]),
    15: ("Clause", ["PP", "Clause"]),
    16: ("Pred", ["VP"]),
    17: ("Pred", []),
    18: ("NP", ["Head", "NP'"]),
    19: ("NP'", ["ADJECTIVE", "NP'"]),
    20: ("NP'", []),
    21: ("Head", ["NOUN"]),
    22: ("Head", ["PRONOUN"]),
    23: ("Head", ["LOCATION"]),
    24: ("Head", ["MONEY_NUMBER"]),
    25: ("VP", ["VERB", "VP'"]),
    26: ("VP'", ["ADJECTIVE", "Comps"]),
    27: ("VP'", ["Comps"]),
    28: ("Comps", ["Comp", "Comps"]),
    29: ("Comps", ["VP"]),
    30: ("Comps", []),
    31: ("Comp", ["NP"]),
    32: ("Comp", ["PP"]),
    33: ("PP", ["PREPOSITION", "NP"]),
}

NONTERMINALS = list(dict.fromkeys(lhs for lhs, _ in GRAMMAR.values()))
TERMINALS = ["NOUN", "PRONOUN", "LOCATION", "MONEY_NUMBER", "VERB", "ADJECTIVE",
             "PREPOSITION", "GREETING_ADDRESS", "DISCOURSE_MARKER",
             "SLANG_INTERJECTION", "TAG_QUESTION", END]

_H = ["NOUN", "PRONOUN", "LOCATION", "MONEY_NUMBER"]
_MARKERS = ["GREETING_ADDRESS", "DISCOURSE_MARKER", "SLANG_INTERJECTION"]
_CLAUSE_END = _MARKERS + ["TAG_QUESTION", END]


def _row(entries):
    """Expand {(t1, t2, ...): prod} into {t1: prod, t2: prod, ...}."""
    row = {}
    for terminals, prod in entries.items():
        for t in terminals:
            row[t] = prod
    return row


# ---------------------------------------------------------------------------
# LL(1) parse table M[nonterminal][terminal] -> production number
# (section 6 of grammar_notes.md)
# ---------------------------------------------------------------------------
TABLE = {
    "S": _row({tuple(_H + ["VERB", "PREPOSITION"] + _MARKERS + ["TAG_QUESTION", END]): 1}),
    "Pre": _row({tuple(_MARKERS): 2,
                 tuple(_H + ["VERB", "PREPOSITION", "TAG_QUESTION", END]): 3}),
    "Marker": {"GREETING_ADDRESS": 4, "DISCOURSE_MARKER": 5, "SLANG_INTERJECTION": 6},
    "Core": _row({tuple(_H + ["VERB", "PREPOSITION"]): 7, ("TAG_QUESTION",): 8, (END,): 9}),
    "Post": _row({tuple(_MARKERS): 10, ("TAG_QUESTION",): 11, (END,): 12}),
    "Clause": _row({tuple(_H): 13, ("VERB",): 14, ("PREPOSITION",): 15}),
    "Pred": _row({("VERB",): 16, tuple(_CLAUSE_END): 17}),
    "NP": _row({tuple(_H): 18}),
    "NP'": _row({("ADJECTIVE",): 19,
                 tuple(_H + ["VERB", "PREPOSITION"] + _CLAUSE_END): 20}),
    "Head": {"NOUN": 21, "PRONOUN": 22, "LOCATION": 23, "MONEY_NUMBER": 24},
    "VP": {"VERB": 25},
    "VP'": _row({("ADJECTIVE",): 26,
                 tuple(_H + ["VERB", "PREPOSITION"] + _CLAUSE_END): 27}),
    "Comps": _row({tuple(_H + ["PREPOSITION"]): 28, ("VERB",): 29, tuple(_CLAUSE_END): 30}),
    "Comp": _row({tuple(_H): 31, ("PREPOSITION",): 32}),
    "PP": {"PREPOSITION": 33},
}


def show_production(num):
    lhs, rhs = GRAMMAR[num]
    return "%s -> %s" % (lhs, " ".join(rhs) if rhs else "epsilon")


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------
def parse(tokens):
    """
    Standard LL(1) stack algorithm.

    tokens: list of (lexeme, CATEGORY) pairs (PARTICLE / UNKNOWN already removed).
    Returns (accepted: bool, message: str, trace: list of (stack, input, action)).
    """
    stream = list(tokens) + [(END, END)]
    stack = [END, START]
    pos = 0
    trace = []

    while stack:
        top = stack[-1]
        lexeme, lookahead = stream[pos]
        snapshot = (" ".join(reversed(stack)),
                    " ".join(t for _, t in stream[pos:]))

        if top == END and lookahead == END:
            trace.append(snapshot + ("ACCEPT",))
            return True, "Accepted", trace

        if top not in TABLE:  # terminal on top of stack
            if top == lookahead:
                stack.pop()
                pos += 1
                trace.append(snapshot + ("match %s '%s'" % (top, lexeme),))
                continue
            msg = "expected %s but found %s '%s' (token %d)" % (top, lookahead, lexeme, pos + 1)
            trace.append(snapshot + ("ERROR: " + msg,))
            return False, msg, trace

        prod = TABLE[top].get(lookahead)
        if prod is None:
            expected = sorted(TABLE[top])
            msg = "no rule for %s on %s '%s' (token %d); expected one of: %s" % (
                top, lookahead, lexeme, pos + 1, ", ".join(expected))
            trace.append(snapshot + ("ERROR: " + msg,))
            return False, msg, trace

        stack.pop()
        rhs = GRAMMAR[prod][1]
        stack.extend(reversed(rhs))
        trace.append(snapshot + ("(%d) %s" % (prod, show_production(prod)),))

    return False, "stack emptied before end of input", trace


def check_sentence(sentence):
    """Tag, filter and parse one sentence."""
    tagged = lexer.analyze_sentence(sentence)
    result = {"sentence": sentence, "tagged": tagged, "tokens": [], "trace": []}

    unknown = [tok for tok, tag in tagged if tag == lexer.UNKNOWN]
    if unknown:
        result["accepted"] = False
        result["message"] = (
            "UNKNOWN token(s) %s: the lexer could not classify them, so they map to "
            "no terminal of the grammar and the parse table has no entry for them. "
            "Add them to the lexicon." % ", ".join("'%s'" % u for u in unknown))
        return result

    # Particles (don/di/dey/na/no/go, le/la/the...) mark tense, aspect, negation
    # or definiteness but do not change phrase structure, so they are skipped.
    tokens = [(tok, tag) for tok, tag in tagged if tag != lexer.PARTICLE]
    result["tokens"] = tokens
    if not tokens:
        result["accepted"] = False
        result["message"] = "no parsable tokens (empty sentence or particles only)"
        return result

    accepted, message, trace = parse(tokens)
    result.update(accepted=accepted, message=message, trace=trace)
    return result


# ---------------------------------------------------------------------------
# Self-check: rebuild FIRST / FOLLOW / table from GRAMMAR and compare to TABLE
# ---------------------------------------------------------------------------
def _first_of_seq(seq, first):
    out = set()
    for sym in seq:
        f = first[sym] if sym in first else {sym}
        out |= f - {EPSILON}
        if EPSILON not in f:
            return out
    out.add(EPSILON)
    return out


def compute_first_follow():
    first = {nt: set() for nt in NONTERMINALS}
    follow = {nt: set() for nt in NONTERMINALS}
    follow[START].add(END)
    changed = True
    while changed:
        changed = False
        for lhs, rhs in GRAMMAR.values():
            new = _first_of_seq(rhs, first)
            if not new <= first[lhs]:
                first[lhs] |= new
                changed = True
            for i, sym in enumerate(rhs):
                if sym not in follow:
                    continue
                rest = _first_of_seq(rhs[i + 1:], first)
                new = (rest - {EPSILON}) | (follow[lhs] if EPSILON in rest else set())
                if not new <= follow[sym]:
                    follow[sym] |= new
                    changed = True
    return first, follow


def verify_table():
    """Return a list of problems (conflicts or mismatches); empty means OK."""
    first, follow = compute_first_follow()
    built, problems = {nt: {} for nt in NONTERMINALS}, []
    for num, (lhs, rhs) in GRAMMAR.items():
        f = _first_of_seq(rhs, first)
        lookaheads = (f - {EPSILON}) | (follow[lhs] if EPSILON in f else set())
        for t in lookaheads:
            if t in built[lhs]:
                problems.append("conflict M[%s, %s]: %d vs %d" % (lhs, t, built[lhs][t], num))
            built[lhs][t] = num
    for nt in NONTERMINALS:
        if built[nt] != TABLE.get(nt):
            problems.append("TABLE row %s differs from the computed row" % nt)
    return problems


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------
def print_trace(result):
    print("Sentence : %s" % result["sentence"])
    print("Tagged   : %s" % " ".join("%s/%s" % (tok, tag) for tok, tag in result["tagged"]))
    print("Parsed on: %s" % " ".join(tag for _, tag in result["tokens"]))
    if result["trace"]:
        print("\n  %-40s %-40s %s" % ("STACK (top at right)", "INPUT", "ACTION"))
        for stack, inp, action in result["trace"]:
            print("  %-40s %-40s %s" % (_clip(stack, 40), _clip(inp, 40), action))
    print("\nResult   : %s - %s" % ("ACCEPTED" if result["accepted"] else "REJECTED",
                                    result["message"]))


def _clip(text, width, keep_end=True):
    if len(text) <= width:
        return text
    return "..." + text[-(width - 3):] if keep_end else text[:width - 3] + "..."


def run_dataset():
    problems = verify_table()
    print("LL(1) table self-check: %s" % ("OK (no conflicts, matches grammar)"
                                          if not problems else "FAILED"))
    for p in problems:
        print("   - " + p)
    print()

    rows = lexer.load_sentences()
    if rows:
        print("Dataset: %d sentences from data/collected_sentences.csv\n" % len(rows))
    else:
        print("Dataset is empty - using built-in demo sentences (not part of the corpus).\n")
        rows = lexer.demo_rows()

    results = []
    for row in rows:
        res = check_sentence(row["sentence"])
        res.update(id=row["id"], topic=row["topic"])
        results.append(res)

    accepted = sum(r["accepted"] for r in results)
    rejected = len(results) - accepted
    unknown = sum(1 for r in results if "UNKNOWN" in r["message"])

    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("  Total     : %d" % len(results))
    print("  Accepted  : %d (%.1f%%)" % (accepted, 100.0 * accepted / len(results)))
    print("  Rejected  : %d (%.1f%%)" % (rejected, 100.0 * rejected / len(results)))
    print("    - of which due to UNKNOWN tokens: %d" % unknown)
    print("    - of which syntax errors        : %d" % (rejected - unknown))
    print()

    print("SAMPLE RESULTS")
    header = "%-7s %-9s %-40s %s" % ("ID", "RESULT", "SENTENCE", "TERMINALS / REASON")
    print(header)
    print("-" * len(header))
    for r in results[:20]:
        detail = (" ".join(t for _, t in r["tokens"]) if r["accepted"] else r["message"])
        print("%-7s %-9s %-40s %s" % (r["id"], "ACCEPTED" if r["accepted"] else "REJECTED",
                                      _clip(r["sentence"], 40, False), _clip(detail, 90, False)))
    print()

    sample = next((r for r in results if r["accepted"]), None)
    if sample:
        print("EXAMPLE PARSE TRACE")
        print("-" * 60)
        print_trace(sample)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    if len(sys.argv) > 1:
        print_trace(check_sentence(" ".join(sys.argv[1:])))
    else:
        run_dataset()
