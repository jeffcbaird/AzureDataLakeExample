"""
Generate realistic sample CSVs in data/local/bronze/<source>/<date>/.

Sources generated:
  - sales        (orders with amounts, statuses, timestamps)
  - inventory    (products with stock levels, SKUs)
  - customers    (CRM records with names, tiers, regions)

Intentionally includes ~5% bad rows per source to exercise the validation
and quarantine pipeline.

Run: make seed  OR  ENV=local python scripts/seed_local_data.py
"""
from __future__ import annotations

import csv
import os
import random
import string
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from lakehouse_common.config.settings import Settings

random.seed(42)
settings = Settings()
TODAY = date.today()


def _rand_id(prefix: str = "") -> str:
    return prefix + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))


def _rand_date(days_back: int = 30) -> str:
    d = TODAY - timedelta(days=random.randint(0, days_back))
    t = datetime(d.year, d.month, d.day, random.randint(0, 23), random.randint(0, 59), tzinfo=timezone.utc)
    return t.isoformat()


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"  wrote {len(rows):>4} rows → {path}")


def seed_sales(bronze_root: Path, n: int = 200) -> None:
    statuses = ["pending", "confirmed", "shipped", "delivered", "cancelled"]
    rows = []
    for i in range(n):
        bad = i % 20 == 0  # ~5% bad rows
        rows.append({
            "order_id":    _rand_id("ORD-"),
            "customer_id": _rand_id("CUST-"),
            "product_id":  _rand_id("PROD-"),
            "quantity":    random.randint(1, 50),
            "unit_price":  "" if bad else round(random.uniform(1.0, 999.99), 2),
            "amount":      "" if bad else round(random.uniform(1.0, 49999.99), 2),
            "status":      "INVALID_STATUS" if bad else random.choice(statuses),
            "order_date":  _rand_date(),
            "ingested_at": datetime.now(timezone.utc).isoformat(),
        })
    write_csv(bronze_root / "sales" / str(TODAY) / "sales.csv", rows)


def seed_inventory(bronze_root: Path, n: int = 150) -> None:
    categories = ["electronics", "clothing", "food", "furniture", "sporting"]
    rows = []
    for i in range(n):
        bad = i % 20 == 0
        rows.append({
            "product_id":    _rand_id("PROD-"),
            "sku":           _rand_id("SKU-"),
            "name":          f"Product {_rand_id()}",
            "category":      "UNKNOWN" if bad else random.choice(categories),
            "stock_qty":     -1 if bad else random.randint(0, 1000),
            "reorder_level": random.randint(5, 50),
            "unit_cost":     round(random.uniform(0.5, 499.99), 2),
            "last_updated":  _rand_date(7),
            "ingested_at":   datetime.now(timezone.utc).isoformat(),
        })
    write_csv(bronze_root / "inventory" / str(TODAY) / "inventory.csv", rows)


def seed_customers(bronze_root: Path, n: int = 100) -> None:
    tiers = ["bronze", "silver", "gold", "platinum"]
    regions = ["north", "south", "east", "west", "central"]
    rows = []
    for i in range(n):
        bad = i % 20 == 0
        rows.append({
            "customer_id": _rand_id("CUST-"),
            "first_name":  f"First{i}",
            "last_name":   f"Last{i}",
            "email":       "" if bad else f"user{i}@example.com",
            "tier":        "UNKNOWN" if bad else random.choice(tiers),
            "region":      random.choice(regions),
            "signup_date": _rand_date(365),
            "ingested_at": datetime.now(timezone.utc).isoformat(),
        })
    write_csv(bronze_root / "customers" / str(TODAY) / "customers.csv", rows)


def main() -> None:
    bronze_root = Path(settings.bronze_path())
    print(f"Seeding bronze data → {bronze_root}")
    seed_sales(bronze_root)
    seed_inventory(bronze_root)
    seed_customers(bronze_root)
    print("Done. Run 'make bronze-silver' to process.")


if __name__ == "__main__":
    main()
