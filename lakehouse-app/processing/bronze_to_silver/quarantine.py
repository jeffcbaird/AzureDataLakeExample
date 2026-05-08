"""Write quarantined rows to the quarantine Delta table."""

from __future__ import annotations

from pyspark.sql import DataFrame


def write_quarantine(
    df: DataFrame,
    quarantine_base_path: str,
) -> int:
    """Append *df* to the quarantine Delta table, partitioned by _source and _date.

    Parameters
    ----------
    df:
        DataFrame of rows that failed ERROR-severity validation rules.  Must
        contain ``_source`` and ``_date`` metadata columns (added by
        schema_enforcement.read_bronze).
    quarantine_base_path:
        Root path of the quarantine container (local dir or abfss URI).

    Returns
    -------
    int
        Number of rows written.
    """
    count = df.count()
    if count == 0:
        return 0

    path = f"{quarantine_base_path.rstrip('/')}/bronze_rejected/"

    (
        df.write.format("delta")
        .mode("append")
        .partitionBy("_source", "_date")
        .save(path)
    )
    return count
