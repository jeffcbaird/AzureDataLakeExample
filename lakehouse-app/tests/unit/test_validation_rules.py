"""Unit tests for validation rules and the validation runner."""
from __future__ import annotations

import pytest
from pyspark.sql import Row, SparkSession

from lakehouse_common.validation.base_rule import Severity, ValidationRule
from lakehouse_common.validation.runner import run_validation
from validation.rules.bronze_rules import get_bronze_rules
from validation.rules.silver_rules import get_silver_rules


# ── Helpers ───────────────────────────────────────────────────────────────────


def _sales_row(**kwargs) -> Row:
    defaults = dict(
        _id=1,
        order_id="ORD-001",
        customer_id="C1",
        product_id="P1",
        quantity=2,
        unit_price=10.0,
        amount=20.0,
        status="shipped",
        order_date="2024-01-15",
        ingested_at="2024-01-15T02:00:00",
        _corrupt_record=None,
        _source="sales",
        _date="2024-01-15",
        _bronze_path="/tmp/bronze/",
    )
    defaults.update(kwargs)
    return Row(**defaults)


def _inventory_row(**kwargs) -> Row:
    defaults = dict(
        _id=1,
        product_id="P1",
        sku="SKU-001",
        name="Widget",
        category="Electronics",
        stock_qty=100,
        reorder_level=10,
        unit_cost=5.0,
        last_updated="2024-01-15T00:00:00",
        ingested_at="2024-01-15T02:00:00",
        _corrupt_record=None,
        _source="inventory",
        _date="2024-01-15",
        _bronze_path="/tmp/bronze/",
    )
    defaults.update(kwargs)
    return Row(**defaults)


# ── Runner behaviour ──────────────────────────────────────────────────────────


def test_error_row_goes_to_quarantine(spark: SparkSession):
    """A row failing an ERROR rule must land in quarantine, not clean_df."""
    rules = get_bronze_rules("sales")
    # unit_price=None triggers positive_unit_price (ERROR)
    rows = [
        _sales_row(_id=1, order_id="ORD-GOOD", unit_price=9.99),
        _sales_row(_id=2, order_id="ORD-BAD",  unit_price=None),
    ]
    df = spark.createDataFrame(rows)
    clean_df, quarantine_df, dq_df = run_validation(df, rules, "bronze_sales", spark)

    clean_ids = {r["order_id"] for r in clean_df.collect()}
    quarantine_ids = {r["order_id"] for r in quarantine_df.collect()}

    assert "ORD-GOOD" in clean_ids
    assert "ORD-BAD" in quarantine_ids
    assert "ORD-BAD" not in clean_ids


def test_warning_row_stays_in_clean(spark: SparkSession):
    """A row failing a WARNING rule must stay in clean_df (with a flag)."""
    rules = get_bronze_rules("sales")
    # status="INVALID_STATUS" triggers valid_status (WARNING)
    rows = [_sales_row(_id=1, status="INVALID_STATUS")]
    df = spark.createDataFrame(rows)
    clean_df, quarantine_df, dq_df = run_validation(df, rules, "bronze_sales", spark)

    assert clean_df.count() == 1
    assert quarantine_df.count() == 0


def test_dq_results_row_count(spark: SparkSession):
    """dq_results must have one row per rule."""
    rules = get_bronze_rules("sales")
    rows = [_sales_row(_id=1)]
    df = spark.createDataFrame(rows)
    _, _, dq_df = run_validation(df, rules, "bronze_sales", spark)

    assert dq_df.count() == len(rules)


def test_dq_results_schema(spark: SparkSession):
    rules = get_bronze_rules("sales")[:1]
    df = spark.createDataFrame([_sales_row(_id=1)])
    _, _, dq_df = run_validation(df, rules, "bronze_sales", spark)

    expected_cols = {"run_id", "table_name", "rule_name", "severity", "passed", "failing_count", "run_timestamp"}
    assert expected_cols.issubset(set(dq_df.columns))


def test_inventory_negative_stock_goes_to_quarantine(spark: SparkSession):
    """non_negative_stock_qty is ERROR — negative rows quarantined."""
    rules = get_bronze_rules("inventory")
    rows = [
        _inventory_row(_id=1, product_id="P-GOOD", stock_qty=5),
        _inventory_row(_id=2, product_id="P-BAD",  stock_qty=-1),
    ]
    df = spark.createDataFrame(rows)
    clean_df, quarantine_df, _ = run_validation(df, rules, "bronze_inventory", spark)

    clean_ids = {r["product_id"] for r in clean_df.collect()}
    quarantine_ids = {r["product_id"] for r in quarantine_df.collect()}

    assert "P-GOOD" in clean_ids
    assert "P-BAD" in quarantine_ids


def test_silver_sales_rules_registered():
    rules = get_silver_rules("sales")
    names = {r.name for r in rules}
    assert "positive_amount" in names
    assert "no_null_order_date" in names


def test_silver_inventory_rules_registered():
    rules = get_silver_rules("inventory")
    names = {r.name for r in rules}
    assert "no_null_sku" in names
    assert "positive_unit_cost" in names


def test_unknown_source_returns_empty_silver_rules():
    """get_silver_rules must not raise for unknown sources."""
    rules = get_silver_rules("unknown_source")
    assert rules == []
