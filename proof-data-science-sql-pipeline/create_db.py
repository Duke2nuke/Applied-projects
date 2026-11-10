"""Create the synthetic retail database (data.db, local only, not committed).

Tables: customers (40), products (12), orders (300). All data is synthetic
and generated with a fixed seed, so the pipeline is reproducible.
"""

import random
import sqlite3
from pathlib import Path

SEED = 42
HERE = Path(__file__).parent
DB = HERE / "data.db"

CATEGORIES = ["Electronics", "Clothing", "Home", "Sports"]
PRODUCTS = [
    ("Headphones", "Electronics", 49.99),
    ("Keyboard", "Electronics", 79.99),
    ("Mouse", "Electronics", 29.99),
    ("T-Shirt", "Clothing", 19.99),
    ("Jeans", "Clothing", 59.99),
    ("Jacket", "Clothing", 89.99),
    ("Lamp", "Home", 34.99),
    ("Mug Set", "Home", 24.99),
    ("Cushion", "Home", 14.99),
    ("Yoga Mat", "Sports", 39.99),
    ("Dumbbells", "Sports", 69.99),
    ("Bottle", "Sports", 12.99),
]


def main(db_path=DB):
    rng = random.Random(SEED)
    if db_path.exists():
        db_path.unlink()
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.executescript(
        """
        CREATE TABLE customers (
            customer_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            city TEXT NOT NULL,
            signup_days_ago INTEGER NOT NULL
        );
        CREATE TABLE products (
            product_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            unit_price REAL NOT NULL
        );
        CREATE TABLE orders (
            order_id INTEGER PRIMARY KEY,
            customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
            product_id INTEGER NOT NULL REFERENCES products(product_id),
            quantity INTEGER NOT NULL,
            order_date TEXT NOT NULL,
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
            FOREIGN KEY (product_id) REFERENCES products(product_id)
        );
        """
    )
    cities = ["Chennai", "Delhi", "Bengaluru", "Mumbai", "Pune"]
    for cid in range(1, 41):
        cur.execute(
            "INSERT INTO customers VALUES (?, ?, ?, ?)",
            (cid, f"Customer {cid:02d}", rng.choice(cities), rng.randint(30, 900)),
        )
    for pid, (name, cat, price) in enumerate(PRODUCTS, start=1):
        cur.execute(
            "INSERT INTO products VALUES (?, ?, ?, ?)", (pid, name, cat, price)
        )
    for oid in range(1, 301):
        cur.execute(
            "INSERT INTO orders VALUES (?, ?, ?, ?, ?)",
            (
                oid,
                rng.randint(1, 40),
                rng.randint(1, 12),
                rng.randint(1, 5),
                f"2026-{rng.randint(1, 10):02d}-{rng.randint(1, 28):02d}",
            ),
        )
    con.commit()
    counts = {
        t: cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        for t in ("customers", "products", "orders")
    }
    con.close()
    print(f"Created {db_path}: {counts}")
    return counts


if __name__ == "__main__":
    main()
