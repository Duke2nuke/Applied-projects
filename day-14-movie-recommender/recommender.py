"""Item-based collaborative filtering movie recommender, stdlib only.

Synthetic data: 60 users rate a subset of 40 movies. Each user has a
latent affinity for each of 6 genres and each movie belongs to 1-2
genres, so ratings are driven by genre taste plus noise. The model
learns item-item cosine similarity on mean-centred ratings and predicts
a user's rating for an unseen movie from the similar movies they
already rated.

Nothing here is a real rating: every movie, user and rating is
generated from a fixed seed and labelled synthetic.
"""

import math
import random

GENRES = ["Action", "Comedy", "Drama", "Sci-Fi", "Horror", "Romance"]

# 40 invented titles, each with 1-2 genres. No real catalogue is used.
MOVIES = [
    ("Steel Horizon", ["Action", "Sci-Fi"]),
    ("Night Pursuit", ["Action"]),
    ("The Last Checkpoint", ["Action", "Drama"]),
    ("Harbour Lights", ["Drama", "Romance"]),
    ("Paper Moons", ["Romance", "Comedy"]),
    ("The Quiet Room", ["Drama"]),
    ("Orbit Nine", ["Sci-Fi"]),
    ("The Cartographer", ["Drama", "Sci-Fi"]),
    ("Laugh Track", ["Comedy"]),
    ("The Family Recipe", ["Comedy", "Drama"]),
    ("Basement Door", ["Horror"]),
    ("The Hollow Field", ["Horror", "Drama"]),
    ("Static", ["Horror", "Sci-Fi"]),
    ("Sunset Tango", ["Romance"]),
    ("The Second Date", ["Romance", "Comedy"]),
    ("Iron Valley", ["Action", "Drama"]),
    ("The Long Detour", ["Comedy"]),
    ("Gravity Well", ["Sci-Fi", "Drama"]),
    ("The Neighbour's Dog", ["Comedy"]),
    ("Cold Storage", ["Horror"]),
    ("The Grand Tour", ["Comedy", "Romance"]),
    ("Ember City", ["Sci-Fi", "Action"]),
    ("The Widow's Garden", ["Drama"]),
    ("Signal Lost", ["Sci-Fi", "Horror"]),
    ("The Apprentice Chef", ["Comedy", "Drama"]),
    ("Red Line", ["Action"]),
    ("The Lighthouse Keeper", ["Drama", "Romance"]),
    ("Midnight Ferry", ["Horror", "Drama"]),
    ("The Optimist", ["Comedy"]),
    ("Deep Field", ["Sci-Fi"]),
    ("The Backup Plan", ["Romance", "Comedy"]),
    ("Stone River", ["Action", "Drama"]),
    ("The Last Laugh", ["Comedy", "Horror"]),
    ("Parallel Lines", ["Sci-Fi", "Romance"]),
    ("The Small Hours", ["Drama"]),
    ("Freefall", ["Action", "Sci-Fi"]),
    ("The Book Club", ["Comedy", "Drama"]),
    ("Widow's Peak", ["Horror"]),
    ("The Long Way Home", ["Drama", "Romance"]),
    ("Zero Hour", ["Action"]),
]

N_USERS = 60
SEED = 42


def _round_half(x):
    """Round to the nearest 0.5, the way star ratings are usually shown."""
    return round(x * 2) / 2


def generate_ratings(seed=SEED, n_users=N_USERS, per_user=(12, 25)):
    """Generate synthetic (user, movie, rating) triples.

    Each user has a clear taste profile: 2 favourite genres (affinity
    +0.8 to +1.0), 1 disliked genre (-1.0 to -0.8), and mild feelings
    (-0.3 to +0.3) about the rest. A movie's rating is 3.0 plus 1.2x
    the user's mean affinity over the movie's genres, plus Gaussian
    noise (sigma 0.4), clipped to [1, 5] and rounded to the nearest
    half star. That gives the data real genre structure for the
    recommender to recover, while keeping ratings noisy like real
    ones. Seeded, so every run reproduces the same data.
    """
    rng = random.Random(seed)
    affinities = {}
    for u in range(n_users):
        a = {g: rng.uniform(-0.3, 0.3) for g in GENRES}
        favourites = rng.sample(GENRES, 2)
        for g in favourites:
            a[g] = rng.uniform(0.8, 1.0)
        disliked = rng.choice([g for g in GENRES if g not in favourites])
        a[disliked] = rng.uniform(-1.0, -0.8)
        affinities[u] = a
    ratings = {}
    for u in range(n_users):
        n = rng.randint(*per_user)
        for m in rng.sample(range(len(MOVIES)), n):
            genres = MOVIES[m][1]
            taste = sum(affinities[u][g] for g in genres) / len(genres)
            raw = 3.0 + 1.2 * taste + rng.gauss(0, 0.4)
            ratings[(u, m)] = _round_half(min(5.0, max(1.0, raw)))
    return ratings, affinities


def train_test_split(ratings, seed=SEED, test_fraction=0.2):
    """Split rating keys 80/20. Splitting ratings (not users) means every
    user keeps some training ratings, so the model can personalise."""
    rng = random.Random(seed + 1)
    keys = sorted(ratings)
    rng.shuffle(keys)
    cut = int(len(keys) * test_fraction)
    test_keys = set(keys[:cut])
    train = {k: v for k, v in ratings.items() if k not in test_keys}
    test = {k: v for k, v in ratings.items() if k in test_keys}
    return train, test


def user_means(train):
    """Mean training rating per user."""
    sums, counts = {}, {}
    for (u, _), r in train.items():
        sums[u] = sums.get(u, 0.0) + r
        counts[u] = counts.get(u, 0) + 1
    return {u: sums[u] / counts[u] for u in sums}


def global_mean(train):
    return sum(train.values()) / len(train)


def item_similarity(train, min_co_raters=2, shrink=5):
    """Adjusted-cosine item-item similarity.

    Each user's ratings are centred on that user's mean, so a harsh
    rater and a generous rater still agree on relative taste. Similarity
    is computed only over users who rated both movies, and only kept
    when at least ``min_co_raters`` did. Raw cosine is shrunk by
    n / (n + shrink) so a similarity seen from only a couple of
    co-raters counts for less than one seen from many. Returns
    {(i, j): sim} with sim in [-1, 1] and sim(i, i) = 1.
    """
    means = user_means(train)
    by_item = {}
    for (u, m), r in train.items():
        by_item.setdefault(m, {})[u] = r - means[u]
    sims = {}
    items = sorted(by_item)
    for a in items:
        sims[(a, a)] = 1.0
        for b in items:
            if b <= a:
                continue
            common = set(by_item[a]) & set(by_item[b])
            if len(common) < min_co_raters:
                continue
            num = sum(by_item[a][u] * by_item[b][u] for u in common)
            den = math.sqrt(sum(by_item[a][u] ** 2 for u in common)) * math.sqrt(
                sum(by_item[b][u] ** 2 for u in common)
            )
            if den > 0:
                raw = num / den
                sims[(a, b)] = sims[(b, a)] = raw * len(common) / (
                    len(common) + shrink
                )
    return sims


def predict(user, movie, train, sims, means, gmean, min_sim=0.05,
            top_k=10):
    """Predict a user's rating for a movie.

    Weighted average of the user's centred ratings on the top-k most
    similar movies they rated, added back to the user's mean. Falls
    back to the user's mean when no similar rated movie exists, and
    to the global mean for a user with no training ratings at all
    (cold start).
    """
    if user not in means:
        return gmean
    rated = [(m, r) for (u, m), r in train.items() if u == user]
    neighbours = sorted(
        ((sims.get((movie, m), 0.0), m, r) for m, r in rated
         if sims.get((movie, m), 0.0) > min_sim),
        reverse=True,
    )[:top_k]
    num = sum(s * (r - means[user]) for s, _, r in neighbours)
    den = sum(abs(s) for s, _, _ in neighbours)
    if den == 0:
        return means[user]
    return min(5.0, max(1.0, means[user] + num / den))


def recommend(user, train, sims, means, gmean, n=5):
    """Top-n movies the user has not rated in training, by predicted
    rating. Returns [(movie_id, predicted_rating), ...]."""
    rated = {m for (u, m) in train if u == user}
    scored = [
        (m, predict(user, m, train, sims, means, gmean))
        for m in range(len(MOVIES))
        if m not in rated
    ]
    scored.sort(key=lambda t: (-t[1], t[0]))
    return scored[:n]


def popularity(train, min_ratings=5):
    """Cold-start fallback: movies by mean training rating, requiring at
    least ``min_ratings`` ratings so one 5-star rating cannot top the
    chart. Returns [(movie_id, mean_rating, count), ...]."""
    sums, counts = {}, {}
    for (_, m), r in train.items():
        sums[m] = sums.get(m, 0.0) + r
        counts[m] = counts.get(m, 0) + 1
    ranked = [
        (m, sums[m] / counts[m], counts[m])
        for m in sums
        if counts[m] >= min_ratings
    ]
    ranked.sort(key=lambda t: (-t[1], -t[2], t[0]))
    return ranked


def rmse(pairs):
    """Root mean squared error over (actual, predicted) pairs."""
    return math.sqrt(sum((a - p) ** 2 for a, p in pairs) / len(pairs))


def evaluate(train, test, sims, means, gmean):
    """RMSE of the model vs two baselines, plus Precision@5 / Recall@5.

    A held-out rating counts as 'liked' at >= 4 stars. For each user
    with at least one liked test rating, the top-5 recommendations are
    checked against their liked test movies.
    """
    model_pairs = [
        (r, predict(u, m, train, sims, means, gmean)) for (u, m), r in test.items()
    ]
    global_pairs = [(r, gmean) for r in test.values()]
    user_pairs = [(r, means.get(u, gmean)) for (u, _), r in test.items()]
    liked = {}
    for (u, m), r in test.items():
        if r >= 4.0:
            liked.setdefault(u, set()).add(m)
    precisions, recalls = [], []
    for u, liked_set in liked.items():
        recs = {m for m, _ in recommend(u, train, sims, means, gmean, n=5)}
        hits = len(recs & liked_set)
        precisions.append(hits / 5)
        recalls.append(hits / len(liked_set))
    return {
        "model_rmse": rmse(model_pairs),
        "global_mean_rmse": rmse(global_pairs),
        "user_mean_rmse": rmse(user_pairs),
        "precision_at_5": sum(precisions) / len(precisions),
        "recall_at_5": sum(recalls) / len(recalls),
        "users_evaluated": len(precisions),
        "test_ratings": len(test),
    }
