"""K-means clustering from scratch (Python standard library only).

Why from scratch: the point of this project is to show the algorithm,
not to call it. Standardisation, k-means++ initialisation, Lloyd
iterations, inertia, and a silhouette score are all implemented here
in plain code, so each step can be explained in an interview.

Standardisation matters: without it, income (tens of k$) would swamp
spending score (1-100) in the distance calculation, even though both
features matter for segmentation.
"""

import math
import random


def standardise(points):
    """Return (scaled points, means, stds) with zero mean, unit variance."""
    dims = len(points[0])
    means = [sum(p[d] for p in points) / len(points) for d in range(dims)]
    stds = [
        math.sqrt(sum((p[d] - means[d]) ** 2 for p in points) / len(points))
        or 1.0
        for d in range(dims)
    ]
    scaled = [tuple((p[d] - means[d]) / stds[d] for d in range(dims))
              for p in points]
    return scaled, means, stds


def _dist(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def _kmeans_plus_plus(points, k, rng):
    """Pick k starting centroids, biased towards points far from those
    already picked (k-means++). Avoids the bad luck of purely random
    starts landing two centroids in the same dense blob."""
    centroids = [rng.choice(points)]
    while len(centroids) < k:
        weights = [min(_dist(p, c) ** 2 for c in centroids) for p in points]
        total = sum(weights)
        pick = rng.random() * total
        for point, weight in zip(points, weights):
            pick -= weight
            if pick <= 0:
                centroids.append(point)
                break
        else:
            centroids.append(points[-1])
    return centroids


def kmeans(points, k, seed=42, max_iter=100):
    """Cluster scaled points. Returns (labels, centroids, inertia).

    inertia = sum of squared distances to the assigned centroid;
    lower is tighter. It always falls as k grows, which is why the
    elbow method (and silhouette) is needed to choose k, not inertia
    alone.
    """
    rng = random.Random(seed)
    centroids = _kmeans_plus_plus(points, k, rng)
    labels = [0] * len(points)
    for _ in range(max_iter):
        new_labels = [
            min(range(k), key=lambda c: _dist(p, centroids[c]))
            for p in points
        ]
        new_centroids = []
        for c in range(k):
            members = [p for p, lab in zip(points, new_labels) if lab == c]
            if members:
                new_centroids.append(tuple(
                    sum(p[d] for p in members) / len(members)
                    for d in range(len(points[0]))
                ))
            else:
                new_centroids.append(centroids[c])  # keep empty cluster alive
        if new_labels == labels and new_centroids == centroids:
            break
        labels, centroids = new_labels, new_centroids
    inertia = sum(_dist(p, centroids[lab]) ** 2
                  for p, lab in zip(points, labels))
    return labels, centroids, inertia


def silhouette(points, labels, k):
    """Mean silhouette score in [-1, 1]. Near 1 = tight, well-separated
    clusters; near 0 = overlapping clusters; negative = misassigned.
    O(n^2) but fine for a 200-point demo."""
    n = len(points)
    scores = []
    for i, p in enumerate(points):
        same = [j for j in range(n) if labels[j] == labels[i] and j != i]
        if not same:
            continue
        a = sum(_dist(p, points[j]) for j in same) / len(same)
        b = min(
            sum(_dist(p, points[j]) for j in range(n) if labels[j] == c)
            / sum(1 for lab in labels if lab == c)
            for c in range(k) if c != labels[i]
        )
        scores.append((b - a) / max(a, b))
    return sum(scores) / len(scores) if scores else 0.0


def unscale(centroid, means, stds):
    """Convert a centroid back to original feature units."""
    return tuple(round(m + c * s, 1) for c, m, s in zip(centroid, means, stds))
