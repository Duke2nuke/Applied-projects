# Day 03 — Resume–Job Description Matcher (ML, Python)

Rank job postings against a resume, and show the skill gaps for the
top matches — so instead of applying everywhere, you apply where you
fit and know exactly what to learn first.

## What it does

- Ranks postings by TF-IDF cosine similarity to the resume
  (`matcher.py`). TF-IDF is implemented by hand with the standard
  library only — no scikit-learn, nothing to install.
- Extracts skills from both texts against a skill vocabulary and
  reports matched vs missing skills per posting, so the ranking
  comes with an explanation, not just a number (`matcher.py`).
- Demo data (`data.py`) is SYNTHETIC and fictional: a made-up
  candidate profile and six made-up postings. Nothing here is a real
  person's resume or a real company's job description. Swap in your
  own resume text and real postings to use it for a real search.
- Tests: `python -m unittest test_matcher -v`

## Run it

```bash
python run.py
python -m unittest test_matcher -v
```

## Results (measured by running `python run.py` on this machine)

Ranking of the six synthetic postings against the synthetic sample
resume:

| Rank | Posting | Cosine score |
| --- | --- | --- |
| 1 | Machine Learning Intern | 0.3162 |
| 2 | Data Science Intern | 0.3078 |
| 3 | Computer Vision Research Intern | 0.0747 |
| 4 | Frontend Developer Intern | 0.0581 |
| 5 | DevOps Intern | 0.0408 |
| 6 | Backend Developer Intern | 0.0150 |

- Top match skill gaps: data visualization, deep learning.
- Tests: 6 passed, 0 failed.
- Read the top two scores honestly: 0.3162 vs 0.3078 is nearly a
  tie. The matcher says "ML and Data Science both fit, ML slightly
  more" — it does not say "ML is clearly the one". A ranking this
  close should be treated as a shortlist of two, not a decision.

## 2-minute explainer (for interviews)

1. The problem is retrieval, not classification. A resume is not
   "in or out" for one role; the question is which of many postings
   fits best, and what is missing. So this is a small search engine
   over job descriptions, with the resume as the query.
2. TF-IDF turns each text into a vector: words that appear a lot in
   one document but rarely elsewhere get high weight, so "scikit-learn"
   counts far more than "experience". Cosine similarity then measures
   the angle between the resume vector and each posting vector —
   direction, not length, so a long posting does not win just for
   being long.
3. The score alone is not enough to act on, so there is a second,
   explainable layer: a skill vocabulary matched as phrases
   ("machine learning", "scikit-learn") against both texts. That is
   what turns "0.32" into "you match on Python, pandas and
   scikit-learn, and you are missing deep learning".
4. I used smoothed IDF — log((1+N)/(1+df)) + 1 — instead of plain
   log(N/df), because with short texts a term in every document
   would otherwise get weight zero, and a shared core skill like
   Python should still count for something.

## Limits

- Bag of words: it cannot tell that "built a classifier" and
  "model development experience" mean similar things, and it has no
  stemming ("built" vs "build" are different tokens).
- Keyword matching can be gamed and can mislead: a posting that
  lists many skills you happen to mention can outrank a better
  real fit, and synonyms ("ML" vs "machine learning") are missed.
- The skill vocabulary is hand-written and fixed — a skill not in
  the list is invisible to the gap analysis.
- Synthetic demo only: the scores above describe made-up texts, not
  real hiring outcomes. Real postings need cleaning (boilerplate,
  equal-opportunity text) before ranking means anything.
- This ranks fit, it does not judge whether a role is real, open,
  or worth applying to — that check still has to happen separately.
