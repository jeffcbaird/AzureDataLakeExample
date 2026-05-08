"""Unit tests for processing.bronze_to_silver.schema_enforcement."""
from __future__ import annotations

import json
import os
import tempfile

import pytest
from pyspark.sql import SparkSession

from processing.bronze_to_silver.schema_enforcement import (
    SOURCE_SCHEMAS,
    read_bronze,
)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _write_ndjson(tmpdir: str, source: str, date: str, rows: list[dict]) -> str:
    """Write rows as NDJSON into tmpdir/source/date/ and return base path."""
    partition_dir = os.path.join(tmpdir, source, date)
    os.makedirs(partition_dir, exist_ok=True)
    path = os.path.join(partition_dir, "part-00000.json")
    with open(path, "w") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")
    return tmpdir


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_sales_metadata_columns(spark: SparkSession, tmp_path):
    rows = [
        {
            "order_id": "ORD-001",
            "customer_id": "C1",
            "product_id": "P1",
            "quantity": 2,
            "unit_price": 10.0,
            "amount": 20.0,
            "status": "shipped",
            "order_date": "2024-01-15",
            "ingested_at": "2024-01-15T02:00:00",
        }
    ]
    base = _write_ndjson(str(tmp_path), "sales", "2024-01-15", rows)
    df = read_bronze(spark, "sales", "2024-01-15", base)

    assert "_id" in df.columns
    assert "_source" in df.columns
    assert "_date" in df.columns
    assert "_bronze_path" in df.columns

    row = df.collect()[0]
    assert row["_source"] == "sales"
    assert row["_date"] == "2024-01-15"


def test_inventory_metadata_columns(spark: SparkSession, tmp_path):
    rows = [
        {
            "product_id": "P1",
            "sku": "SKU-001",
            "name": "Widget",
            "category": "Electronics",
            "stock_qty": 100,
            "reorder_level": 10,
            "unit_cost": 5.0,
            "last_updated": "2024-01-15T00:00:00",
            "ingested_at": "2024-01-15T02:00:00",
        }
    ]
    base = _write_ndjson(str(tmp_path), "inventory", "2024-01-15", rows)
    df = read_bronze(spark, "inventory", "2024-01-15", base)

    row = df.collect()[0]
    assert row["_source"] == "inventory"
    assert row["product_id"] == "P1"


def test_corrupt_record_column_present(spark: SparkSession, tmp_path):
    """Rows with bad JSON land in _corrupt_record, not as exceptions."""
    rows = [{"order_id": "ORD-001", "unit_price": 9.99}]
    base = _write_ndjson(str(tmp_path), "sales", "2024-01-16", rows)
    df = read_bronze(spark, "sales", "2024-01-16", base)
    # _corrupt_record column must exist (may be null for well-formed rows)
    assert "_corrupt_record" in df.columns


def test_source_literal_is_correct(spark: SparkSession, tmp_path):
    rows = [{"product_id": "P1", "sku": "SKU-1"}]
    base = _write_ndjson(str(tmp_path), "inventory", "2024-01-17", rows)
    df = read_bronze(spark, "inventory", "2024-01-17", base)
    assert df.collect()[0]["_source"] == "inventory"


def test_unknown_source_raises(spark: SparkSession, tmp_path):
    with pytest.raises(ValueError, match="Unknown source"):
        read_bronze(spark, "unicorns", "2024-01-15", str(tmp_path))


def test_all_source_schemas_registered():
    for source in ("sales", "inventory"):
        assert source in SOURCE_SCHEMAS, f"{source} missing from SOURCE_SCHEMAS"
