"""Row-level deduplication using business keys and ingestion timestamp."""

from __future__ import annotations

from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.window import Window

# ── Business keys per source ──────────────────────────────────────────────────
# When a source emits duplicate business keys in the same Bronze file (e.g. a
# re-send), keep the row with the latest ingested_at timestamp.

BUSINESS_KEYS: dict[str, list[str]] = {
    "sales": ["order_id"],
    "inventory": ["product_id", "sku"],
}


def deduplicate(df: DataFrame, source: str) -> DataFrame:
    """Return *df* with at most one row per business key.

    The row with the *latest* ``ingested_at`` value wins.  When two rows share
    both the business key and ``ingested_at``, the one with the higher ``_id``
    (monotonically_increasing_id) is kept, giving deterministic output.

    Parameters
    ----------
    df:
        DataFrame produced by the normalization step (must have ``_id`` and
        ``ingested_at`` columns).
    source:
        Source name used to look up business keys.
    """
    if source not in BUSINESS_KEYS:
        raise ValueError(
            f"No business keys defined for source '{source}'. "
            "Add an entry to BUSINESS_KEYS in deduplication.py."
        )

    keys = BUSINESS_KEYS[source]
    window = Window.partitionBy(*keys).orderBy(
        F.col("ingested_at").desc_nulls_last(),
        F.col("_id").desc(),
    )

    return (
        df.withColumn("_row_num", F.row_number().over(window))
        .filter(F.col("_row_num") == 1)
        .drop("_row_num")
    )
