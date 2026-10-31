# Day 05 — Customer Segmentation with K-Means, from Scratch (Day B: AI/ML Python)

Group customers into segments a business can actually act on, using
K-means implemented from scratch in pure Python — no scikit-learn,
no third-party libraries. Standardisation, k-means++ initialisation,
Lloyd iterations, inertia, and silhouette score are all written out
in `kmeans.py` so every step can be explained, not just called.

This is deliberately different from Days 01–03: those were a
supervised classifier (prompt injection), an anomaly detector, and a
similarity matcher. This one is **unsupervised clustering** — there
are no labels at training time; the structure has to be discovered.

## How to run

```bash
python3 run.py            # elbow table + cluster profiles
python3 test_segment.py   # automated checks
```

Python 3 only, standard library only (`requirements.txt` is empty
on purpose).

## Example output (actually run, 31 Oct 2026)

```
Elbow table (inertia falls as k grows; look for the bend):
  k    inertia  silhouette
  2      361.5       0.369
  3      172.2       0.500
  4      118.0       0.475
  5      107.8       0.441
  6       90.6       0.423
  7       67.3       0.412

Chosen k=4: inertia=118.0, silhouette=0.475

Cluster profiles (centroids in original units):
  cluster 0: n= 55 | age=23.7, annual income (k$)=37.6, spending score=78.1
  cluster 1: n= 49 | age=46.6, annual income (k$)=40.3, spending score=21.6
  cluster 2: n= 49 | age=38.8, annual income (k$)=112.6, spending score=84.8
  cluster 3: n= 47 | age=35.8, annual income (k$)=60.0, spending score=50.4
```

In plain terms: young low-income high-spenders, older low-income
low-spenders, high-income high-spenders, and average-everything
shoppers. A business would treat these differently — e.g. discounts
and budget picks for cluster 0, premium offers for cluster 2, and
retention nudges rather than discounts for cluster 1.

## 2-minute interview explainer

**Problem.** A shop has customer data (age, income, spending score)
but no labels — nobody has tagged who is a "premium" vs "budget"
customer. How do you find useful groups anyway?

**Approach.** (1) Standardise every feature to zero mean and unit
variance, otherwise income (tens of k$) would swamp spending score
(1–100) in the distance maths. (2) Initialise centroids with
k-means++, which spreads starting points apart instead of risking
two centroids in the same blob. (3) Alternate assigning each point
to its nearest centroid and moving each centroid to its cluster's
mean, until nothing moves. (4) Choose k with the elbow method plus
silhouette score, not inertia alone — inertia always falls as k
grows, so it can never pick k by itself.

**Results.** On 200 clearly-labelled synthetic customers (see
Limits), k=4 gives silhouette 0.475 and recovers the planted
segments well: clusters are 49/55, 47/49, 49/49, and 43/47 pure.
The automated test checks inertia decreases with k, no cluster is
empty, silhouette exceeds 0.25, and the run is reproducible from
its fixed seed.

**Limits.** The data is synthetic with well-separated planted
segments, so real customer data would score worse and need
cleaning, outlier handling, and feature selection first. The
silhouette score actually peaks at k=3 (0.500) rather than k=4
(0.475) — k=4 is chosen because the elbow bends there and it
recovers all four planted segments, but on unlabelled real data
that trade-off would need a judgement call, not a formula. K-means
also assumes roughly spherical, equally-sized clusters and is
sensitive to outliers and to the initialisation seed; a production
version would run several restarts and keep the lowest-inertia one.

## Data honesty

All 200 customers are synthetic, generated in `data.py` from four
planted segments with a fixed seed. No real customer data is used.
