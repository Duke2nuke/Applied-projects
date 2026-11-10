# Data Science + SQL Pipeline — proof project

End-to-end data-science pipeline on a **synthetic** retail dataset
(40 customers, 12 products, 300 orders, fixed seed — no real customer data):

**SQLite → SQL joins/aggregations → Pandas EDA → scikit-learn model → Matplotlib chart.**

## What it proves

- **SQL**: multi-table joins, `GROUP BY` aggregations, ordering/limits — see `queries.sql` (revenue by category, top-5 customers by spend, average order value by city).
- **Pandas**: loading SQL results, group-bys, missing-value checks.
- **Machine Learning**: Ridge regression predicting order total from quantity, unit price, customer tenure and product category (one-hot), with a held-out test split.
- **Visualisation**: actual-vs-predicted chart (`chart.svg`).

## Measured result

Run `python create_db.py && python analysis.py` — real numbers, measured 10 Nov 2026:

- Orders: 300, total revenue: **38,593.03** (synthetic currency units)
- Ridge regression, 60 held-out orders: **RMSE 27.90, R² 0.8973**
- Missing values: 0

## Run it

```bash
pip install -r requirements.txt
python create_db.py      # builds data.db locally (not committed)
python analysis.py       # EDA + model, writes metrics.json + chart.svg
python test_pipeline.py  # rebuilds everything, asserts RMSE < 40 and R² > 0.85
```

## Honest caveats

- All data is synthetic and generated with a fixed seed; revenue figures are illustrative, not real sales.
- The target (order total = quantity × unit price) is multiplicative, so a linear Ridge model cannot fit it perfectly — hence RMSE 27.90 rather than near zero. That is the honest result of this model choice.
- `data.db` is generated locally and is not committed.
