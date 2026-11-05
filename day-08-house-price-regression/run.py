"""Train and evaluate the Day 08 house-price regression.

Usage: python3 run.py
Prints gradient-descent vs closed-form weights (original units),
test-set MAE / RMSE / R^2, and the true weights for comparison.
All data is synthetic (see data.py); nothing here is a real price.
"""

from data import FEATURES, TRUE_INTERCEPT, TRUE_WEIGHTS, generate, train_test_split
from regression import (
    StandardScaler,
    closed_form,
    gradient_descent,
    mae,
    predict,
    r2,
    rmse,
    to_original_units,
)


def main():
    X, y = generate(n=200, seed=42)
    X_train, X_test, y_train, y_test = train_test_split(X, y)
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    w_gd = gradient_descent(X_train_s, y_train, lr=0.05, epochs=2000)
    w_cf = closed_form(X_train_s, y_train)

    for label, w in [("Gradient descent", w_gd), ("Closed form     ", w_cf)]:
        intercept, weights = to_original_units(w, scaler)
        pred = predict(w, X_test_s)
        print(f"{label}: intercept=${intercept:,.0f}")
        for name, coef in zip(FEATURES, weights):
            print(f"    {name:12s} ${coef:>10,.1f} per unit")
        print(
            f"    test MAE=${mae(y_test, pred):,.0f}  "
            f"RMSE=${rmse(y_test, pred):,.0f}  R^2={r2(y_test, pred):.3f}"
        )

    print(f"\nTrue model    : intercept=${TRUE_INTERCEPT:,.0f}")
    for name, coef in zip(FEATURES, TRUE_WEIGHTS):
        print(f"    {name:12s} ${coef:>10,.1f} per unit")
    print(
        f"\nTrain n={len(X_train)}, test n={len(X_test)}; "
        "noise sigma=$15,000 (see data.py)."
    )


if __name__ == "__main__":
    main()
