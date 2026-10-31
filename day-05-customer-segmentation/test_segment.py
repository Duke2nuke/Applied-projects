"""Tests for the segmentation project. Run:  python3 test_segment.py"""

from data import generate
from kmeans import kmeans, silhouette, standardise


def main():
    customers, _ = generate()
    assert len(customers) == 200, "expected 200 synthetic customers"
    scaled, _, _ = standardise(customers)

    # Inertia must fall as k grows (more centroids can only fit tighter).
    inertias = [kmeans(scaled, k)[2] for k in range(2, 8)]
    assert all(b < a for a, b in zip(inertias, inertias[1:])), \
        f"inertia not decreasing: {inertias}"

    # k=4: every point assigned, no empty cluster, decent separation.
    labels, _, _ = kmeans(scaled, 4)
    assert len(labels) == 200 and set(labels) == {0, 1, 2, 3}
    assert silhouette(scaled, labels, 4) > 0.25, "clusters overlap too much"

    # Deterministic: same seed reproduces the same clustering.
    assert kmeans(scaled, 4)[0] == labels, "run is not reproducible"

    print("All tests passed.")
    print(f"  inertia k=2..7: {[round(v, 1) for v in inertias]}")
    print(f"  silhouette k=4: {silhouette(scaled, labels, 4):.3f}")


if __name__ == "__main__":
    main()
