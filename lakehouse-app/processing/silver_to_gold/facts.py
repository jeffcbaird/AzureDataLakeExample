"""Fact table writers for the Gold tier.

Strategy: append + ``replaceWhere`` over a rolling 7-day window.
This avoids full-table rewrites while ensuring late-arriving data within
the window is correctly reflected.
"""

from __future__ import annotations

from datetime import date, timedelta

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F


_WINDOW_DAYS = 7


def write_fact_partition(
    spark: SparkSession,
    df: DataFrame,
    target_path: str,
    date_col: str = "_date",
    processing_date: str | None = None,
) -> int:
    """Write *df* to a Gold fact Delta table using a 7-day ``replaceWhere`` window.

    Only rows whose *date_col* falls within the rolling window are replaced.
    Rows outside the window are untouched, preventing accidental historical
    rewrites from a bug in incremental logic.

    Parameters
    ----------
    spark:
        Active SparkSession.
    df:
        Fact rows to write. Must contain *date_col*.
    target_path:
        Delta table path (local dir or abfss URI).
    date_col:
        Partition column (string ISO-8601 dates).
    processing_date:
        ISO date string representing "today" (defaults to today's UTC date).
        The window covers [processing_date - 6 days, processing_date].

    Returns
    -------
    int
        Number of rows written.
    """
    if processing_date is None:
        processing_date = date.today().isoformat()

    window_start = (
        date.fromisoformat(processing_date) - timedelta(days=_WINDOW_DAYS - 1)
    ).isoformat()

    replace_condition = (
        f"{date_col} >= '{window_start}' AND {date_col} <= '{processing_date}'"
    )

    count = df.count()
    if count == 0:
        return 0

    (
        df.write.format("delta")
        .mode("overwrite")
        .option("replaceWhere", replace_condition)
        .partitionBy(date_col)
        .save(target_path)
    )
    return count


# ── Concrete fact builders ─────────────────────────────────────────────────────


def build_fact_orders(silver_sales_df: DataFrame) -> DataFrame:
    """Select and type-cast Silver sales columns into the fact_orders schema."""
    return silver_sales_df.select(
        F.col("order_id"),
        F.col("customer_id"),
        F.col("product_id"),
        F.col("quantity").cast("long"),
        F.col("unit_price").cast("double"),
        F.col("amount").cast("double"),
        F.col("status"),
        F.col("order_date").cast("date").alias("order_date"),
        F.col("_date"),
    )
