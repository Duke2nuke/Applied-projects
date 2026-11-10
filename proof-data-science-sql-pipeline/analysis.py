"""End-to-end data-science pipeline: SQL -> Pandas EDA -> scikit-learn model.

1. Loads order lines from SQLite with SQL joins (see queries.sql).
2. Pandas EDA: shape, revenue by category, missing-value check.
3. Ridge regression predicting order total from quantity, unit price,
   customer tenure and product category (one-hot).
4. Writes metrics.json and an actual-vs-predicted chart (chart.svg).
"""

import json
import sqlite3
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.linear_model import Ridge  # noqa: E402
from sklearn.metrics import mean_squared_error, r2_score  # noqa: E402
from sklearn.model_selection import train_test_split  # noqa: E402
from sklearn.preprocessing import OneHotEncoder  # noqa: E402

HERE = Path(__file__).parent
DB = HERE / "data.db"

ORDER_LINES_SQL = """
SELECT o.order_id, o.quantity, p.unit_price, p.category,
       c.signup_days_ago, (o.quantity * p.unit_price) AS total
FROM orders o
JOIN products p ON p.product_id = o.product_id
JOIN customers c ON c.customer_id = o.customer_id
"""


def main():
    con = sqlite3.connect(DB)
    n_customers = con.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
    df = pd.read_sql_query(ORDER_LINES_SQL, con)
    con.close()

    eda = {
        "n_orders": int(len(df)),
        "n_customers": int(n_customers),
        "total_revenue": round(float(df["total"].sum()), 2),
        "mean_order_total": round(float(df["total"].mean()), 2),
        "missing_values": int(df.isna().sum().sum()),
        "revenue_by_category": {
            k: round(float(v), 2)
            for k, v in df.groupby("category")["total"].sum().items()
        },
    }

    X_num = df[["quantity", "unit_price", "signup_days_ago"]].to_numpy(dtype=float)
    enc = OneHotEncoder(sparse_output=False, handle_unknown="ignore")
    X_cat = enc.fit_transform(df[["category"]])
    import numpy as np

    X = np.hstack([X_num, X_cat])
    y = df["total"].to_numpy(dtype=float)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    model = Ridge(alpha=1.0)
    model.fit(X_train, y_train)
    pred = model.predict(X_test)
    rmse = float(mean_squared_error(y_test, pred) ** 0.5)
    r2 = float(r2_score(y_test, pred))

    fig, ax = plt.subplots()
    ax.scatter(y_test, pred, s=18)
    ax.plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()], "r--")
    ax.set_xlabel("Actual order total")
    ax.set_ylabel("Predicted order total")
    ax.set_title("Ridge: actual vs predicted order total")
    fig.tight_layout()
    fig.savefig(HERE / "chart.svg")
    plt.close(fig)

    metrics = {**eda, "model": "Ridge(alpha=1.0)", "test_size": len(y_test),
               "rmse": round(rmse, 2), "r2": round(r2, 4)}
    (HERE / "metrics.json").write_text(json.dumps(metrics, indent=2))
    print(f"Orders: {eda['n_orders']}, revenue: {eda['total_revenue']}")
    print(f"Ridge RMSE: {rmse:.2f}, R2: {r2:.4f} ({len(y_test)} held-out orders)")
    return metrics


if __name__ == "__main__":
    main()
