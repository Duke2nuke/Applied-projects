"""Synthetic telecom customer-churn data with a planted, explainable signal.

Churn is driven by things a retention team can actually act on: short
tenure, month-to-month contracts, expensive fibre plans, electronic-check
billing, no tech support, and repeated support calls. The data is fully
synthetic (seeded RNG, no real customers) so the project is honest about
what it proves: the pipeline, not a real-world churn rate.
"""

import numpy as np
import pandas as pd

RNG_SEED = 42
N_CUSTOMERS = 3_000

CONTRACTS = ["month-to-month", "one-year", "two-year"]
INTERNET = ["dsl", "fiber", "none"]
PAYMENTS = ["electronic-check", "mailed-check", "bank-transfer", "credit-card"]


def generate(n: int = N_CUSTOMERS, seed: int = RNG_SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    tenure = rng.integers(0, 73, size=n)
    senior = rng.binomial(1, 0.16, size=n)
    partner = rng.binomial(1, 0.48, size=n)
    dependents = rng.binomial(1, 0.30, size=n)

    contract = rng.choice(CONTRACTS, size=n, p=[0.55, 0.24, 0.21])
    internet = rng.choice(INTERNET, size=n, p=[0.35, 0.45, 0.20])
    payment = rng.choice(PAYMENTS, size=n, p=[0.34, 0.23, 0.21, 0.22])

    # Fibre costs more; no-internet customers pay the least.
    base_charge = np.where(
        internet == "fiber", rng.normal(85, 12, size=n),
        np.where(internet == "dsl", rng.normal(55, 10, size=n),
                 rng.normal(25, 5, size=n)),
    )
    monthly_charges = np.clip(base_charge, 18, 120).round(2)
    total_charges = np.round(tenure * monthly_charges
                             * rng.normal(1.0, 0.05, size=n), 2)

    tech_support = np.where(
        internet == "none", "no-internet",
        rng.choice(["yes", "no"], size=n, p=[0.35, 0.65]),
    )
    support_calls = rng.poisson(lam=1.2, size=n)
    # Unhappy customers call more: extra calls for fibre + no support.
    support_calls += ((internet == "fiber") & (tech_support == "no")) \
        .astype(int) * rng.integers(0, 4, size=n)
    support_calls = np.clip(support_calls, 0, 12)

    # Planted churn signal (log-odds), so the drivers are recoverable.
    logit = (
        -2.6
        - 0.035 * tenure                       # longer tenure -> stays
        + 0.020 * monthly_charges              # expensive plan -> leaves
        + 1.10 * (contract == "month-to-month")
        - 0.70 * (contract == "two-year")
        + 0.55 * (internet == "fiber")
        + 0.60 * (payment == "electronic-check")
        + 0.45 * (tech_support == "no")
        + 0.25 * support_calls                 # each extra call adds risk
        + 0.30 * senior
    )
    p_churn = 1 / (1 + np.exp(-logit))
    churn = rng.binomial(1, p_churn)

    return pd.DataFrame({
        "tenure_months": tenure,
        "monthly_charges": monthly_charges,
        "total_charges": total_charges,
        "contract": contract,
        "internet_service": internet,
        "payment_method": payment,
        "senior_citizen": senior,
        "partner": partner,
        "dependents": dependents,
        "tech_support": tech_support,
        "support_calls": support_calls,
        "churn": churn,
    })


if __name__ == "__main__":
    df = generate()
    print(df.head(5).to_string(index=False))
    print(f"\nrows: {len(df)}, churn rate: {df['churn'].mean():.3f}")
