# Day 14 — Movie Recommender (Day B: AI/ML Python)

A stdlib-only Python recommender system: given synthetic movie ratings
from 60 users, predict how a user would rate a movie they haven't seen
and recommend their top 5. It uses item-based collaborative filtering —
"people who liked the movies you liked also liked…" — with adjusted
cosine similarity on mean-centred ratings.

This is deliberately not a repeat of earlier days: Day 01 classified
text, Day 02 detected anomalies, Day 03 matched text by similarity,
Day 05 clustered customers, Day 08 did tabular regression, Day 10
retrieved documents, and Day 11 forecast a time series. This one is
the missing ML type so far — **recommendation**, where the task is to
rank unseen items for a specific user rather than predict a single
number or label.

## How to run

No dependencies — Python 3.10+ standard library only.

```bash
python run.py            # full report + sample recommendations
python -m unittest test_recommender -v
```

## Example output (actually run, 9 Nov 2026)

```
Movie recommender — item-based collaborative filtering
1163 synthetic ratings, 40 movies, 60 users (931 train / 232 test)
Global mean rating: 3.18

Most similar pair learned: 'Red Line' ~ 'Zero Hour' (sim 0.64) — genres ['Action'] vs ['Action']

Held-out test results (232 ratings):
  model RMSE:       0.648
  global-mean RMSE: 0.710
  user-mean RMSE:   0.738
  Precision@5:      0.153
  Recall@5:         0.506 (34 users with a liked test movie)

Top 5 recommendations for user 0 (mean rating 3.11):
  4.3★  Iron Valley  (Action, Drama)
  4.1★  Red Line  (Action)
  4.0★  The Last Checkpoint  (Action, Drama)
  4.0★  Steel Horizon  (Action, Sci-Fi)
  3.9★  Basement Door  (Horror)

Cold start — a brand-new user gets the most popular movies:
  3.45★ (19 ratings)  The Widow's Garden
  3.41★ (27 ratings)  Laugh Track
  3.38★ (26 ratings)  Signal Lost
  3.37★ (23 ratings)  The Cartographer
  3.31★ (21 ratings)  Gravity Well

Example: user 0 is predicted to rate 'Harbour Lights' 2.89★
```

User 0's recommendations are almost all Action — the model recovered
that user's taste from their ratings alone, without ever seeing their
genre affinities. The one odd pick, Basement Door (Horror), is the
kind of miss that keeps Precision@5 honest.

## How it works

- **Data** (`recommender.py`, `generate_ratings`): 1,163 synthetic
  ratings — 60 users, 40 invented movies in 6 genres. Each user has a
  taste profile (2 favourite genres, 1 disliked, mild feelings about
  the rest); a rating is 3.0 plus 1.2x the user's mean affinity over
  the movie's genres, plus Gaussian noise (σ=0.4), clipped to [1, 5]
  and rounded to half stars. Seeded, so every run reproduces the same
  data. Clearly labelled synthetic; no real ratings are used.
- **Similarity**: adjusted cosine — each user's ratings are centred on
  their own mean first, so a harsh rater and a generous rater still
  agree on relative taste. Computed only over users who rated both
  movies (at least 2), then shrunk by n/(n+5) so a similarity seen
  from a couple of co-raters counts for less than one seen from many.
- **Prediction**: for a user and an unseen movie, a weighted average
  of the user's centred ratings on the 10 most similar movies they
  rated, added back to the user's mean. Falls back to the user's mean
  when nothing similar was rated, and to the global mean for a user
  with no ratings at all (cold start → popularity list instead).
- **Evaluation**: 80/20 split of ratings (not users, so every user
  keeps some training ratings and the model can personalise). RMSE
  against a global-mean and a user-mean baseline, plus Precision@5
  and Recall@5 on held-out movies the user actually liked (≥ 4★).

## Results

| model | RMSE |
|---|---|
| global mean | 0.710 |
| user mean | 0.738 |
| item-based CF | **0.648** |

The model beats both baselines, and the ranking quality is the more
interesting number: Recall@5 of 0.506 means the top-5 list recovers
about half of each user's held-out liked movies, though Precision@5
of 0.153 shows most recommended movies were not in the held-out liked
set — expected when each user only has ~4 held-out ratings and most
of the catalogue is unrated.

Tests: 7/7 pass — determinism, train/test disjointness, similarity
symmetry and bounds, predictions in [1, 5], model beats both
baselines, recommendations exclude already-rated movies and are
ranked, cold-start fallback works.

## Limits

- Synthetic data with planted genre structure — real ratings are
  sparser, messier, and driven by far more than genre.
- Item-based CF cannot recommend a movie nobody has rated yet (the
  item cold-start problem), and a brand-new user only gets the
  popularity list until they rate something.
- No content features are used: two movies are similar only if users
  rated them similarly, so a great new movie in an unpopular genre
  has no way in.
- Ratings are treated as independent; the model ignores when a movie
  was rated, so taste drift over time is invisible.

## 2-minute explainer

**Problem:** a streaming service wants to suggest movies a user will
actually like, from a catalogue they have mostly never seen.
**Approach:** I generated synthetic ratings for 60 users and 40
movies, where each user has favourite and disliked genres, then built
item-based collaborative filtering: centre every user's ratings on
their own mean, measure how similarly each pair of movies is rated,
shrink similarities seen from few co-raters, and predict a rating as
a similarity-weighted average of the movies that user already rated.
**Results:** on held-out ratings it scores RMSE 0.648 against 0.710
for just guessing the global mean, and its top-5 list recovers about
half of each user's held-out liked movies — and you can see it working
in the demo, where user 0 gets almost all Action films, which is their
taste. **Limits:** the data is synthetic and genre-driven, new movies
and new users get no personalised recommendations, and the model
ignores time, so it would miss taste changing over months.
