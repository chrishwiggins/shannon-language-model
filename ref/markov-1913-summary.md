# Markov 1913 — the first Markov chain, on *Eugene Onegin*

**Source grabbed:** https://alpha60.de/research/markov/DavidLink_AnExampleOfStatistical_MarkovTrans_2007.pdf
**Local copy:** `ref/markov-1913-eugene-onegin-statistical-investigation-link-trans-2007.pdf` (+ `.txt` extract)

**Full citation:** A. A. Markov, "An Example of Statistical Investigation of the Text
*Eugene Onegin* Concerning the Connection of Samples in Chains." Lecture at the
physical-mathematical faculty, Royal Academy of Sciences, St. Petersburg, 23 January 1913.
English translation (by Gloria Custance / David Link) published in *Science in Context*
19(4), 591–600 (2006), Cambridge University Press, doi:10.1017/S0269889706001074.

## What Markov did

He took **20,000 letters** from Pushkin's *Eugene Onegin* (the entire first chapter plus
sixteen stanzas of the second), excluding the hard/soft signs, and reduced every letter to
a binary symbol: **vowel or consonant**. He then measured not just how often each occurs,
but how often each *follows* the other — the first empirical demonstration that successive
symbols in a text are **not independent**. This is the origin of what we now call a Markov
chain.

## The figures (from Markov's own text)

- Vowel probability overall: **p = 0.432** (8,638 vowels; 11,362 consonants).
- Vowel-vowel pairs counted: **1,104** → p₁ (vowel after a vowel) = 1104 / 8638 = **0.128**.
- Consonant-consonant pairs: **3,827** → p₀ (vowel after a consonant) = 7534 / 11,362 = **0.663**.
- The dependence: δ = p₁ − p₀ = 0.128 − 0.663 = **−0.535**. A vowel is far *less* likely
  after a vowel than after a consonant — letters constrain their neighbors. Under an
  independence assumption δ would be 0.

## Why it belongs in this project

Markov counted **letters** (vowel/consonant transitions). Shannon, in his 1945 cryptography
memo, turned such transition statistics into a **generator** of language (the n-gram
"approximations to English"). This app's bigram walk is the generative descendant of
Markov's 1913 measurement. *Eugene Onegin* is bundled as a standard text (`dat/markov-onegin.txt`)
precisely so a visitor can run the walk over the very text where the chain was born; the
About / History tab links this paper.
