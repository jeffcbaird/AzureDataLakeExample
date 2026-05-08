"""Unit tests for processing.bronze_to_silver.normalization."""
from __future__ import annotations

import pytest
from pyspark.sql import Row, SparkSession
from pyspark.sql import types as T

from processing.bronze_to_silver.normalization import normalize


# ── Helpers ───────────────────────────────────────────────────────────────────


def _sales_row(**kwargs):
    defaults = {
        "_id": 1,
        "order_id": "ORD-001",
        "customer_id": "  C1  ",
        "product_id": "P1",
        "quantity": 2,
        "unit_price": 10.0,
        "amount": 20.0,
        "status": "SHIPPED",
        "order_date": "2024-01-15",
        "ingested_at": "2024-01-15T02:00:00",
        "_source": "sales",
        "_date": "2024-01-15",
        "_bronze_path": "/tmp/bronze/sales/2024-01-15/",
        "_corrupt_record": None,
    }
    defaults.update(kwargs)
    return Row(**defaults)


def _inventory_row(**kwargs):
    defaults = {
        "_id": 1,
        "product_id": "P1",
        "sku": "  SKU-001  ",
        "name": "Widget",
        "category": "Electronics",
        "stock_qty": 100,
        "reorder_level": 10,
        "unit_cost": 5.0,
        "last_updated": "2024-01-15T00:00:00",
        "ingested_at": "2024-01-15T02:00:00",
        "_source": "inventory",
        "_date": "2024-01-15",
        "_bronze_path": "/tmp/bronze/inventory/2024-01-15/",
        "_corrupt_record": None,
    }
    defaults.update(kwargs)
    return Row(**defaults)


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_sales_status_lowercased(spark: SparkSession):
    df = spark.createDataFrame([_sales_row(status="SHIPPED")])
    result = normalize(df, "sales").collect()[0]
    assert result["status"] == "shipped"


def test_sales_trims_string_columns(spark: SparkSession):
    df = spark.createDataFrame([_sales_row(customer_id="  C1  ", order_id="  ORD-001  ")])
    result = normalize(df, "sales").collect()[0]
    assert result["customer_id"] == "C1"
    assert result["order_id"] == "ORD-001"


def test_sales_order_date_parsed_to_timestamp(spark: SparkSession):
    df = spark.createDataFrame([_sales_row(order_date="2024-01-15")])
    result_df = normalize(df, "sales")
    # TimestampType after parsing — not StringType
    field = next(f for f in result_df.schema.fields if f.name == "order_date")
    assert isinstance(field.dataType, T.TimestampType)


def test_inventory_trims_sku(spark: SparkSession):
    df = spark.createDataFrame([_inventory_row(sku="  SKU-001  ")])
    result = normalize(df, "inventory").collect()[0]
    assert result["sku"] == "SKU-001"


def test_inventory_last_updated_parsed(spark: SparkSession):
    df = spark.createDataFrame([_inventory_row(last_updated="2024-01-15T00:00:00")])
    result_df = normalize(df, "inventory")
    field = next(f for f in result_df.schema.fields if f.name == "last_updated")
    assert isinstance(field.dataType, T.TimestampType)


def test_unknown_source_raises(spark: SparkSession):
    df = spark.createDataFrame([Row(_id=1, foo="bar")])
    with pytest.raises(ValueError, match="No normalizer registered"):
        normalize(df, "unicorns")
