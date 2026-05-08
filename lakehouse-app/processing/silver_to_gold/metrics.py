"""Pre-aggregated metric table builders for the Gold tier.

Each builder reads Silver (or Gold fact) data for the affected date window
and rewrites the metric partition from scratch — metrics are always fully
recomputed, never incrementally updated, to avoid cumulative rounding errors.
"""

from __future__ import annotations

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F


# ── daily_revenue_summary ─────────────────────────────────────────────────────


def build_daily_revenue_summary(fact_orders_df: DataFrame) -> DataFrame:
    """Aggregate fact_orders into a per-day revenue summary.

    Output columns:
        order_date        — date (partition key)
        total_revenue     — sum of amount
        order_count       — count of distinct order_id
        avg_order_value   — total_revenue / order_count
        distinct_customers — count of distinct customer_id
    """
    return (
        fact_orders_df
        .groupBy(F.col("order_date"))
        .agg(
            F.round(F.sum("amount"), 2).alias("total_revenue"),
            F.countDistinct("order_id").alias("order_count"),
            F.round(F.avg("amount"), 2).alias("avg_order_value"),
            F.countDistinct("customer_id").alias("distinct_customers"),
        )
        .withColumn("_date", F.date_format(F.col("order_date"), "yyyy-MM-dd"))
    )


def write_metric(
    spark: SparkSession,
    df: DataFrame,
    target_path: str,
    date_col: str | None = "_date",
) -> int:
    """Overwrite the metric Delta table at *target_path*.

    When *date_col* is provided, the table is partitioned by that column so
    individual date slices can be selectively replaced on backfill.
    When *date_col* is ``None`` the table is written without partitioning
    (suitable for non-temporal tables such as ``customer_features``).
    """
    count = df.count()
    if count == 0:
        return 0

    writer = (
        df.write.format("delta")
        .mode("overwrite")
        .option("overwriteSchema", "true")
    )

    if date_col is not None:
        writer = writer.partitionBy(date_col)

    writer.save(target_path)
    return count


# ── customer_features (ML feature table) ─────────────────────────────────────


def build_customer_features(fact_orders_df: DataFrame) -> DataFrame:
    """Compute per-customer ML features from the full fact_orders history.

    Output columns:
        customer_id           — string (PK)
        total_orders          — count of distinct order_id
        total_spend           — sum of amount
        avg_order_value       — mean amount per order
        last_order_date       — most recent order_date
        distinct_products     — count of distinct product_id
        feature_refreshed_at  — timestamp of this computation run
    """
    return (
        fact_orders_df
        .groupBy("customer_id")
        .agg(
            F.countDistinct("order_id").alias("total_orders"),
            F.round(F.sum("amount"), 2).alias("total_spend"),
            F.round(F.avg("amount"), 2).alias("avg_order_value"),
            F.max("order_date").alias("last_order_date"),
            F.countDistinct("product_id").alias("distinct_products"),
        )
        .withColumn("feature_refreshed_at", F.current_timestamp())
    )
