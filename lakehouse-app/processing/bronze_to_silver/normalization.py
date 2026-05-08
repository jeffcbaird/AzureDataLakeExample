"""Field-level normalization applied after Bronze validation."""

from __future__ import annotations

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

# ── Shared helpers ────────────────────────────────────────────────────────────

_STRING_COLS_BY_SOURCE: dict[str, list[str]] = {
    "sales": ["order_id", "customer_id", "product_id", "status"],
    "inventory": ["product_id", "sku", "name", "category"],
}


def _trim_strings(df: DataFrame, source: str) -> DataFrame:
    """Strip leading/trailing whitespace from all known string columns."""
    cols = _STRING_COLS_BY_SOURCE.get(source, [])
    for col in cols:
        if col in df.columns:
            df = df.withColumn(col, F.trim(F.col(col)))
    return df


def _parse_timestamps(df: DataFrame, ts_cols: list[str]) -> DataFrame:
    """Cast ISO-8601 string columns to TimestampType."""
    for col in ts_cols:
        if col in df.columns:
            df = df.withColumn(col, F.to_timestamp(F.col(col)))
    return df


# ── Source-specific normalizers ───────────────────────────────────────────────


def normalize_sales(df: DataFrame) -> DataFrame:
    """Normalize a sales Bronze DataFrame into Silver shape."""
    df = _trim_strings(df, "sales")
    # Lower-case status for consistent downstream filtering.
    df = df.withColumn("status", F.lower(F.col("status")))
    # Parse temporal fields.
    df = _parse_timestamps(df, ["order_date", "ingested_at"])
    return df


def normalize_inventory(df: DataFrame) -> DataFrame:
    """Normalize an inventory Bronze DataFrame into Silver shape."""
    df = _trim_strings(df, "inventory")
    df = _parse_timestamps(df, ["last_updated", "ingested_at"])
    return df


# ── Dispatch ──────────────────────────────────────────────────────────────────

_NORMALIZERS = {
    "sales": normalize_sales,
    "inventory": normalize_inventory,
}


def normalize(df: DataFrame, source: str) -> DataFrame:
    """Dispatch to the correct normalizer for *source*."""
    if source not in _NORMALIZERS:
        raise ValueError(
            f"No normalizer registered for source '{source}'. "
            "Add one to _NORMALIZERS in normalization.py."
        )
    return _NORMALIZERS[source](df)
