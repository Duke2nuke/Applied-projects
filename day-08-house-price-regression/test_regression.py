"""Automated checks for Day 08. Run: python3 test_regression.py"""

from data import TRUE_WEIGHTS, generate, train_test_split
from regression import (
    StandardScaler,
    closed_form,
    gradient_descent,
    mae,
    predict,
    r2,
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

    # 1. Gradient descent must land close to the exact closed-form answer.
    pred_gd = predict(w_gd, X_test_s)
    pred_cf = predict(w_cf, X_test_s)
    mean_diff = sum(abs(a - b) for a, b in zip(pred_gd, pred_cf)) / len(pred_gd)
    assert mean_diff < 2000, f"GD vs closed-form mean diff too large: {mean_diff}"

    # 2. The model must actually explain the synthetic prices.
    assert r2(y_test, pred_cf) > 0.85, f"R^2 too low: {r2(y_test, pred_cf)}"
    assert mae(y_test, pred_cf) < 20000, f"MAE too high: {mae(y_test, pred_cf)}"

    # 3. Recovered signs must match the true model: size +, age -, distance -.
    _, weights = to_original_units(w_cf, scaler)
    assert weights[0] > 0, "size coefficient should be positive"
    assert weights[2] < 0, "age coefficient should be negative"
    assert weights[3] < 0, "distance coefficient should be negative"

    # 4. Recovered size weight must be in the right ballpark (true: 150).
    assert 100 < weights[0] < 200, f"size weight off: {weights[0]}"

    # 5. Scaler must round-trip: transform then invert recovers the input.
    row = X_train[0]
    scaled = scaler.transform([row])[0]
    back = [s * std + mean for s, std, mean in zip(scaled, scaler.stds_, scaler.means_)]
    assert all(abs(a - b) < 1e-9 for a, b in zip(row, back)), "scaler round-trip failed"

    print(
        f"All 5 checks passed: GD-vs-closed-form mean diff=${mean_diff:,.0f}, "
        f"test R^2={r2(y_test, pred_cf):.3f}, MAE=${mae(y_test, pred_cf):,.0f}"
    )


if __name__ == "__main__":
    main()
