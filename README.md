# How a Language Model Walks

A teaching demo for the simplest possible language model: a **bigram Markov chain**.
A bigram model is a map (each word points to the words seen right after it); generating
text is a random walk over that map. The app animates the walk, moving a reading head
through the training text one word at a time as each next word is sampled.

**Live demo:** https://shannon-language-model.pages.dev (password: `monday`)

## What it shows

- **A bigram model is a map.** Build a directed graph whose nodes are words and whose
  edges go from each word to the words seen right after it. A word's *out-degree* (its
  number of distinct next-words) is the branching factor of the model.
- **Generation is a random walk.** Sample each next word in proportion to how often it
  followed the current one; the reading head moves through the training text as it goes.
  This is exactly Shannon's 1948 first-order word model: no temperature, no neural net.
- **A designed training text** makes the branching legible. The text is engineered so
  most words have a small, near-uniform out-degree (mostly two choices), so you can
  follow the walk by eye. A self-check recomputes the bigram graph from the displayed
  tokens and proves it matches the designed graph, or blocks generation.
- **The covering walk.** To exhibit *every* edge in the fewest words, the displayed text
  is a Guan-route-augmented Eulerian circuit (route inspection + Hierholzer) over the
  designed graph.
- **Real text, for contrast.** Other tabs build the real bigram graph of pasted text or
  a bundled public-domain classic, where out-degrees vary wildly (Zipfian), unlike the
  uniform designed demo.

## Running it locally

The designed-demo and paste tabs work from any static server. The standard-texts tab
reads bundled files from `dat/`, and the optional URL-scraping tab uses Python's
BeautifulSoup (which cannot run in a browser). The local backend serves everything:

```
python3 src/server.py
# then open http://localhost:8731/
```

The only non-stdlib dependency is `beautifulsoup4` (`pip install beautifulsoup4`), and
only the URL tab needs it.

To produce the static build that the live site serves:

```
python3 src/build-static.py # writes out/site/
```

The static build removes the URL-scraping tab (no Python backend on a static host) and
stamps a last-updated time.

The app is behind a client-side password gate (password: `monday`). This is obfuscation,
not security: the password ships in the page source.

## Project layout

| Path | What it is |
|---|---|
| `index.html` | The single-page app (markup + CSS + JS). |
| `src/server.py` | Local dev backend: serves the app and the URL scraper (BeautifulSoup). |
| `src/build-static.py` | Produces the static deploy build in `out/site/`. |
| `src/pareto-entropy.py` | Computes the fair-use-vs-branching Pareto front (Shannon conditional entropy vs. vocabulary) over a text. |
| `dat/*.txt` | Bundled public-domain training texts. |
| `dat/index.json` | Catalog the Standard-texts tab reads. |
| `ref/markov-1913-summary.md` | A short note on Markov's 1913 *Eugene Onegin* chain (the first Markov chain). |

## The training texts

All bundled texts in `dat/` are public domain:

- `markov-onegin.txt` — Pushkin's *Eugene Onegin* (Henry Spalding's 1881 translation),
  the text Andrey Markov used in 1913 for the first Markov chain.
- `bible-genesis.txt` — King James Bible, Genesis 1.
- `shakespeare-hamlet.txt`, `shakespeare-sonnet18.txt` — Shakespeare.
- `house-jack.txt` — "The House That Jack Built" (1755, a cumulative rhyme).
- `ring-roses.txt` — "Ring a Ring o' Roses".
- `columbia-mission.txt` — the Columbia University mission statement.

The designed demo's small vocabulary is drawn from a canon of texts about language,
machines, and meaning (Chomsky, Brautigan, Orwell via Strunk & White, the 1955 Dartmouth
proposal, Weizenbaum, Searle, Strachey). Those copyrighted sources are **referenced by
title and used only as the provenance of individual words; none of their text is
redistributed here.**

## Background

- A. A. Markov (1913) counted vowel/consonant transitions across 20,000 letters of
  *Eugene Onegin* — the first Markov chain. See `ref/markov-1913-summary.md`.
- C. E. Shannon (1948), *A Mathematical Theory of Communication* — the n-gram language
  model and conditional entropy this demo animates.

## License

MIT (see `LICENSE`) for the code. The bundled `dat/*.txt` training texts are public-domain
works, included as data.
