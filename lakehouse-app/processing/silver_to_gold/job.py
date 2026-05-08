"""Silver → Gold processing job.

Entry point for ``make silver-gold`` (local) and Synapse Spark Job Definition (Azure).

Pipeline
--------
1. Read incremental Silver sales and inventory partitions for *date*.
2. Run Gold validation rules on each Silver source.
3. MERGE dim_product (SCD1) and dim_customer (SCD2).
4. Write fact_orders using the 7-day replaceWhere window.
5. Recompute daily_revenue_summary and customer_features metrics.
6. Update _table_registry entries for every Gold table written.

Environment variables
---------------------
DATE    ISO-8601 processing date (required).
ENV     ``local`` (default) or ``azure``.
"""

from __future__ import annotations

import os
import sys

from pyspark.sql import SparkSession, functions as F

from lakehouse_common.config.settings import Settings
from lakehouse_common.validation.runner import run_validation

from .dimensions import merge_scd1, merge_scd2
from .facts import build_fact_orders, write_fact_partition
from .metrics import (
    build_customer_features,
    build_daily_revenue_summary,
    write_metric,
)
from .table_registry import write_registry_entry
from validation.rules.gold_rules import get_gold_rules


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise EnvironmentError(f"Required environment variable '{name}' is not set.")
    return value


def run(date: str) -> dict[str, int]:
    """Execute the full Silver → Gold pipeline for *date*.

    Returns a summary dict with row counts for each Gold table written.
    """
    settings = Settings()

    spark = (
        SparkSession.builder.appName(f"silver_to_gold_{date}")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config(
            "spark.sql.catalog.spark_catalog",
            "org.apache.spark.sql.delta.catalog.DeltaCatalog",
        )
        .getOrCreate()
    )

    summary: dict[str, int] = {}

    # ── 1. Load Silver partitions ─────────────────────────────────────────────
    silver_sales = (
        spark.read.format("delta")
        .load(settings.silver_path("sales"))
        .filter(F.col("_date") == date)
    )

    silver_inventory = (
        spark.read.format("delta")
        .load(settings.silver_path("inventory"))
        .filter(F.col("_date") == date)
    )

    # ── 2. Gold validation on Silver inputs ───────────────────────────────────
    sales_gold_rules = get_gold_rules("sales")
    if sales_gold_rules:
        silver_sales, _, _ = run_validation(
            silver_sales, sales_gold_rules, "gold_sales_input", spark
        )

    inventory_gold_rules = get_gold_rules("inventory")
    if inventory_gold_rules:
        silver_inventory, _, _ = run_validation(
            silver_inventory, inventory_gold_rules, "gold_inventory_input", spark
        )

    # ── 3. dim_product (SCD Type 1) ───────────────────────────────────────────
    dim_product_source = silver_inventory.select(
        F.col("product_id"),
        F.col("sku"),
        F.col("name"),
        F.col("category"),
        F.col("unit_cost"),
    ).dropDuplicates(["product_id"])

    dim_product_path = settings.gold_path("dim_product")
    merge_scd1(
        spark,
        dim_product_source,
        dim_product_path,
        business_key="product_id",
        update_cols=["sku", "name", "category", "unit_cost"],
    )
    dim_product_count = spark.read.format("delta").load(dim_product_path).count()
    summary["dim_product"] = dim_product_count

    # ── 4. dim_customer (SCD Type 2) ─────────────────────────────────────────
    dim_customer_source = silver_sales.select(
        F.col("customer_id"),
        F.col("status").alias("last_known_status"),
    ).dropDuplicates(["customer_id"])

    dim_customer_path = settings.gold_path("dim_customer")
    merge_scd2(
        spark,
        dim_customer_source,
        dim_customer_path,
        business_key="customer_id",
        track_cols=["last_known_status"],
    )
    dim_customer_count = (
        spark.read.format("delta").load(dim_customer_path)
        .filter(F.col("is_current") == True)
        .count()
    )
    summary["dim_customer"] = dim_customer_count

    # ── 5. fact_orders ────────────────────────────────────────────────────────
    fact_orders_df = build_fact_orders(silver_sales)
    fact_orders_path = settings.gold_path("fact_orders")
    fact_count = write_fact_partition(spark, fact_orders_df, fact_orders_path, processing_date=date)
    summary["fact_orders"] = fact_count

    # ── 6. Metrics — read full fact table for accurate aggregates ─────────────
    full_fact_orders = spark.read.format("delta").load(fact_orders_path)

    revenue_df = build_daily_revenue_summary(full_fact_orders)
    revenue_path = settings.gold_path("daily_revenue_summary")
    summary["daily_revenue_summary"] = write_metric(spark, revenue_df, revenue_path)

    features_df = build_customer_features(full_fact_orders)
    features_path = settings.gold_path("customer_features")
    summary["customer_features"] = write_metric(
        spark, features_df, features_path, date_col=None
    )

    # ── 7. _table_registry ────────────────────────────────────────────────────
    registry_path = settings.table_registry_path()

    table_meta = {
        "dim_product": ("data-engineering", "06:00", "SCD1 product dimension from inventory Silver."),
        "dim_customer": ("data-engineering", "06:00", "SCD2 customer dimension tracking status changes."),
        "fact_orders": ("data-engineering", "06:00", "Order fact table — 7-day replaceWhere window."),
        "daily_revenue_summary": ("analytics", "07:00", "Pre-aggregated daily revenue KPIs."),
        "customer_features": ("ml-platform", "08:00", "Per-customer ML feature store snapshot."),
    }

    for table_name, count in summary.items():
        owner, sla, desc = table_meta[table_name]
        write_registry_entry(spark, registry_path, table_name, count, owner, sla, desc)

    spark.stop()
    return summary


if __name__ == "__main__":
    date = _require_env("DATE")
    summary = run(date)
    print(f"silver_to_gold complete: {summary}")
    sys.exit(0)
