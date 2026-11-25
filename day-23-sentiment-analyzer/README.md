# Day 23 — Sentiment Analyzer (Day B: AI/ML Python)

Binary sentiment classification (positive / negative) of short review
sentences: TF-IDF + Logistic Regression vs Multinomial Naive Bayes,
trained and evaluated on 3,000 real labelled sentences.

## The problem

Every product, support desk and app store gets short one-line reviews.
Reading them one by one does not scale; a classifier that tags each
sentence positive/negative lets you count sentiment per product, per
week, or per source, and surface the angriest ones first.

## The data

UCI "Sentiment Labelled Sentences" (Kotzias et al., KDD 2015) — 1,000
sentences each from Amazon product reviews, IMDb movie reviews and
Yelp restaurant reviews, labelled 0 = negative, 1 = positive.
Files are used unchanged in `data/`; see `data/DATA_SOURCE.md`.

## Approach

1. Load the 3,000 sentences (stratified 80/20 train/test split, seed 42).
2. TF-IDF vectorizer: word unigrams + bigrams (so "not good" is one
   feature, not "not" + "good"), `min_df=2`, sublinear TF.
3. Two models, same features: Logistic Regression (C=1.0) and
   Multinomial Naive Bayes (alpha=0.1).
4. Report accuracy, macro F1, confusion matrix, and accuracy per
   source (Amazon / IMDb / Yelp) — a model that only works on one kind
   of review is not a general sentiment model.

## Results (actually run, 600 held-out sentences)

| Model | Accuracy | Macro F1 | Amazon | IMDb | Yelp |
|---|---|---|---|---|---|
| Logistic Regression | **0.835** | 0.8349 | 0.864 | 0.792 | 0.848 |
| Multinomial NB | 0.8017 | 0.8017 | 0.804 | 0.802 | 0.799 |

LogReg confusion matrix `[[TN, FP], [FN, TP]] = [[245, 55], [44, 256]]` —
errors are fairly balanced between false positives and false negatives.
IMDb is the hardest source (movie reviews are longer and more
sarcastic/figurative); Amazon the easiest. Full numbers in
`metrics.json`, including the per-class report.

## Limits

- Short sentences only: the model was trained on one-liners, so long
  reviews, sarcasm and mixed sentiment ("great food, awful service")
  are often misclassified — there is no neutral or mixed class.
- Small data (3,000 sentences) and a bag-of-words model: it has no
  word order beyond bigrams and no understanding of context.
- A 0.835 on this dataset is not a production sentiment score; it is
  a baseline. A transformer fine-tune would beat it, at 100x the cost.

## How to run

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Train + evaluate both models, writes metrics.json
python sentiment.py eval

# Predict one sentence (trains on all 3,000 rows first, ~2s)
python sentiment.py predict "I love this, it works great"
# positive (p=0.982)

python sentiment.py predict "Terrible, broke after one day, total waste of money"
# negative (p=0.868)

python sentiment.py predict --model nb "The food was amazing and the staff were lovely"
# positive (p=0.990)

# Tests (14 tests)
python -m unittest test_sentiment -v
```

Tested with Python 3.12, scikit-learn 1.9.1.

## 2-minute explainer

**Problem:** short review sentences arrive faster than anyone can read
them, and you need a positive/negative tag per sentence to track
sentiment. **Approach:** I used the UCI Sentiment Labelled Sentences
set, 3,000 real one-line reviews from Amazon, IMDb and Yelp. I turned
text into TF-IDF features with unigrams and bigrams, because "not
good" means the opposite of "good", then trained Logistic Regression
and Naive Bayes on the same features with a stratified 80/20 split.
**Results:** Logistic Regression wins at 83.5% accuracy and 0.835
macro F1, Naive Bayes 80.2%; Amazon reviews are easiest at 86.4%,
IMDb hardest at 79.2%. **Limits:** it only handles short sentences,
has no neutral class, and bag-of-words cannot do sarcasm or mixed
sentiment — a fine-tuned transformer would beat it, but this is the
honest baseline you compare that against.
