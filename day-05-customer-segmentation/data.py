"""Synthetic customer data for the segmentation demo.

Clearly synthetic: four planted segments, generated with a fixed seed
so every run reproduces the same 200 customers. No real customer data
is used anywhere in this project.

Features per customer: age (years), annual income (k$), spending score
(1-100, higher = spends more of their income).
"""

import random

# (label, count, mean age, mean income, mean spending, spreads)
SEGMENTS = [
    ("careful_savers", 50, 45, 40, 20, (8, 8, 8)),
    ("standard_shoppers", 50, 35, 60, 50, (8, 8, 8)),
    ("premium_spenders", 50, 40, 110, 85, (8, 10, 8)),
    ("young_splurgers", 50, 24, 35, 80, (5, 8, 8)),
]


def generate(seed=42):
    """Return (customers, true_labels).

    customers: list of (age, income_k, spending_score) tuples.
    true_labels: the planted segment name for each customer, kept only
    so the demo can report how well clustering recovers the segments.
    """
    rng = random.Random(seed)
    customers, labels = [], []
    for name, count, age, income, spending, (sa, si, ss) in SEGMENTS:
        for _ in range(count):
            customers.append((
                max(18, round(rng.gauss(age, sa))),
                max(15, round(rng.gauss(income, si))),
                min(100, max(1, round(rng.gauss(spending, ss)))),
            ))
            labels.append(name)
    return customers, labels


if __name__ == "__main__":
    customers, labels = generate()
    print(f"{len(customers)} synthetic customers, "
          f"{len(set(labels))} planted segments")
    for row, label in list(zip(customers, labels))[:5]:
        print(label, row)
