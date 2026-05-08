"""Unit tests for processing.bronze_to_silver.deduplication."""
from __future__ import annotations

import pytest
from pyspark.sql import Row, SparkSession

from processing.bronze_to_silver.deduplication import BUSINESS_KEYS, deduplicate


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_sales_df(spark: SparkSession, rows: list[dict]):
    return spark.createDataFrame([Row(**r) for r in rows])


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_keeps_latest_ingested_at(spark: SparkSession):
    rows = [
        {"_id": 1, "order_id": "ORD-1", "status": "pending",   "ingested_at": "2024-01-15T01:00:00"},
        {"_id": 2, "order_id": "ORD-1", "status": "shipped",   "ingested_at": "2024-01-15T02:00:00"},
    ]
    df = _make_sales_df(spark, rows)
    result = deduplicate(df, "sales").collect()

    assert len(result) == 1
    assert result[0]["status"] == "shipped"


def test_no_duplicates_unchanged(spark: SparkSession):
    rows = [
        {"_id": 1, "order_id": "ORD-1", "status": "shipped",  "ingested_at": "2024-01-15T01:00:00"},
        {"_id": 2, "order_id": "ORD-2", "status": "pending",  "ingested_at": "2024-01-15T01:00:00"},
    ]
    df = _make_sales_df(spark, rows)
    result = deduplicate(df, "sales").collect()

    assert len(result) == 2


def test_composite_key_inventory(spark: SparkSession):
    """Inventory uses (product_id, sku) as composite key."""
    rows = [
        {"_id": 1, "product_id": "P1", "sku": "SKU-A", "stock_qty": 5,  "ingested_at": "2024-01-15T01:00:00"},
        {"_id": 2, "product_id": "P1", "sku": "SKU-A", "stock_qty": 10, "ingested_at": "2024-01-15T02:00:00"},
        {"_id": 3, "product_id": "P1", "sku": "SKU-B", "stock_qty": 3,  "ingested_at": "2024-01-15T01:00:00"},
    ]
    df = _make_sales_df(spark, rows)
    result = deduplicate(df, "inventory").collect()

    assert len(result) == 2
    kept = {(r["product_id"], r["sku"]): r["stock_qty"] for r in result}
    assert kept[("P1", "SKU-A")] == 10
    assert kept[("P1", "SKU-B")] == 3


def test_tie_broken_by_id(spark: SparkSession):
    """When ingested_at is identical, row with highest _id wins."""
    rows = [
        {"_id": 1, "order_id": "ORD-1", "status": "first",  "ingested_at": "2024-01-15T01:00:00"},
        {"_id": 5, "order_id": "ORD-1", "status": "second", "ingested_at": "2024-01-15T01:00:00"},
    ]
    df = _make_sales_df(spark, rows)
    result = deduplicate(df, "sales").collect()

    assert len(result) == 1
    assert result[0]["status"] == "second"


def test_unknown_source_raises(spark: SparkSession):
    rows = [{"_id": 1, "foo": "bar", "ingested_at": "2024-01-15T01:00:00"}]
    df = _make_sales_df(spark, rows)
    with pytest.raises(ValueError, match="No business keys"):
        deduplicate(df, "unknown_source")


def test_business_keys_defined_for_all_sources():
    for source in ("sales", "inventory"):
        assert source in BUSINESS_KEYS, f"{source} missing from BUSINESS_KEYS"
