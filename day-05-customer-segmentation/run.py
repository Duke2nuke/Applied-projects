"""Run the segmentation demo: elbow table, then k=4 cluster profiles.

Usage:  python3 run.py
"""

from data import generate
from kmeans import kmeans, silhouette, standardise, unscale

FEATURES = ("age", "annual income (k$)", "spending score")


def main():
    customers, true_labels = generate()
    scaled, means, stds = standardise(customers)

    print("Elbow table (inertia falls as k grows; look for the bend):")
    print(f"{'k':>3} {'inertia':>10} {'silhouette':>11}")
    for k in range(2, 8):
        labels, _, inertia = kmeans(scaled, k)
        print(f"{k:>3} {inertia:>10.1f} {silhouette(scaled, labels, k):>11.3f}")

    k = 4
    labels, centroids, inertia = kmeans(scaled, k)
    print(f"\nChosen k={k}: inertia={inertia:.1f}, "
          f"silhouette={silhouette(scaled, labels, k):.3f}\n")
    print("Cluster profiles (centroids in original units):")
    for c in range(k):
        members = [i for i, lab in enumerate(labels) if lab == c]
        centre = unscale(centroids[c], means, stds)
        profile = ", ".join(f"{name}={value}"
                            for name, value in zip(FEATURES, centre))
        # How pure is this cluster vs the planted segments?
        planted = {}
        for i in members:
            planted[true_labels[i]] = planted.get(true_labels[i], 0) + 1
        dominant, count = max(planted.items(), key=lambda kv: kv[1])
        print(f"  cluster {c}: n={len(members):>3} | {profile} | "
              f"mostly {dominant} ({count}/{len(members)})")


if __name__ == "__main__":
    main()
