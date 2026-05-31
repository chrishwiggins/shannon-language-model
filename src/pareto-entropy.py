#!/usr/bin/env python3
"""Pareto frontier: fair use vs. branching, using the empirical conditional
entropy of the bigram source. This is the well-defined version (it replaces the
stationary/Perron-weighted attempt, which was ill-defined: pruning k=1 words to
get a Perron vector fails to punish forced text, and keeping them means no
stationary distribution exists).

Branching is measured by the per-step conditional entropy of the next token given
the current one, weighted by how often each current token actually occurs:

    Hbar = sum_{w1} ( n(w1) / N ) * H[ p(w2 | w1) ]            (bits per step)

with p estimated from the excerpt's bigram counts. This needs no ergodicity and
no recurrent-subgraph surgery: every token has empirical weight n(w1)/N >= 0, and
a dead-end (k=1, out-degree 1) token contributes H = 0, so it DRAGS THE AVERAGE
DOWN -- the text is correctly punished for forced, deterministic stretches. It is
exactly Shannon's conditional entropy H(W2|W1) of the bigram source (A
Mathematical Theory of Communication, 1948). (k here = out-degree.)

Two objectives:
    fair use  = MINIMIZE vocabulary |{w1}|   (fewest distinct words quoted)
    branching = MAXIMIZE Hbar

Excerpts are contiguous whole-sentence runs; the sentence-end "." is a real token.

Usage:
    python3 src/pareto-entropy.py dat/house-jack.txt [label]
"""

import json
import re
import sys
from math import log2
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def split_sentences(raw):
    """Split text into sentences. A sentence runs up to and including a run of
    sentence-ending punctuation (. ! ?). Blank lines, a leading quoted title line,
    and parenthetical stage directions are dropped. Each sentence keeps its
    terminator."""
    lines = []
    for ln in raw.splitlines():
        s = ln.strip()
        if not s:
            continue
        if s.startswith('"') and s.endswith(")"):  # title line in quotes
            continue
        if s.startswith("(") and s.endswith(")"):  # stage direction
            continue
        lines.append(s)
    text = " ".join(lines)
    parts = re.findall(r"[^.!?]*[.!?]+", text)
    return [p.strip() for p in parts if p.strip()]


def words_of(sentence, keep_period):
    """Tokenize one sentence into lowercase words; words keep internal hyphens.
    With keep_period, a single '.' token is appended to mark the sentence end."""
    body = re.sub(r"[.!?]+$", "", sentence)
    toks = re.findall(r"[a-z][a-z\-]*", body.lower())
    return toks + ["."] if keep_period else toks


def empirical_conditional_entropy(stream):
    """Hbar = sum_w1 (n(w1)/N) H[p(w2|w1)] in bits/step, and vocabulary |{w1}|.
    No Perron vector; dead-ends counted and punished (they contribute 0).

    Edge cases in H[p(w2|w1)], stated explicitly:
      - out-degree k=1 (exactly one successor): p(w2|w1)=1, so H = -1*log2(1) = 0.
        This is forced, not a convention: a deterministic next word carries no
        surprise.
      - out-degree k=0 (a terminal token: it appears, but never as a predecessor,
        so there is no w2 at all): the conditional distribution is empty and H is
        undefined. We set H := 0 by the standard convention (0 log 0 = 0; the empty
        sum is 0). Such a token contributes 0 to Hbar; its final occurrence is not
        a bigram step, so it is excluded from the weight denominator N = steps.
    The net effect: forced (k=1) and dead-end (k=0) tokens both pull Hbar toward 0,
    which is the intended punishment for deterministic text."""
    counts = {}  # w1 -> {w2: n}
    for a, b in zip(stream, stream[1:]):
        counts.setdefault(a, {})
        counts[a][b] = counts[a].get(b, 0) + 1
    # weight by occurrences that have a successor (i.e. not the very last token's
    # final appearance). N = number of bigram steps = len(stream) - 1.
    steps = max(len(stream) - 1, 1)
    hbar = 0.0
    for w1, succ in counts.items():
        tot = sum(succ.values())
        h = -sum((c / tot) * log2(c / tot) for c in succ.values())
        hbar += (tot / steps) * h   # tot = number of times w1 was a predecessor
    vocab = len(set(stream))
    return hbar, vocab


def frontier(sentences, keep_period):
    sent_words = [words_of(s, keep_period) for s in sentences]
    n = len(sentences)
    pts = []
    for span in range(1, n + 1):
        for start in range(0, n - span + 1):
            stream = [w for sw in sent_words[start:start + span] for w in sw]
            h, vocab = empirical_conditional_entropy(stream)
            pts.append((vocab, h, len(stream), span, start))
    pts.sort(key=lambda p: (p[0], -p[1]))
    front, best = [], -1.0
    for p in pts:
        if p[1] > best + 1e-9:
            front.append(p)
            best = p[1]
    return front


def main():
    src = Path(sys.argv[1])
    label = sys.argv[2] if len(sys.argv) > 2 else src.stem
    sentences = split_sentences(src.read_text(encoding="utf-8"))
    front = frontier(sentences, True)  # period convention (the app's model)
    print(f"[{label}] {len(sentences)} sentences; Pareto (min vocab, max Hbar bits/step):")
    print(f'{"vocab":>5} {"Hbar":>7} {"tokens":>6} {"sents":>5} {"start":>5}')
    pairs = []
    for vocab, h, tok, span, start in front:
        print(f'{vocab:5d} {h:7.3f} {tok:6d} {span:5d} {start:5d}')
        pairs.append([vocab, round(h, 3)])
    if front:
        knee = max(front, key=lambda p: (p[1] / p[0] if p[0] else 0, p[1]))
        v, h, tok, span, start = knee
        print(f"  knee (max Hbar per word): vocab {v}, {h:.3f} bits/step, "
              f"{span} sentence(s) from #{start}")
        print(f"  excerpt: {' '.join(sentences[start:start + span])}")
    print(f'  PARETO = {json.dumps(pairs)}')


if __name__ == "__main__":
    main()
