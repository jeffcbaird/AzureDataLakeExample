"""SCD Type 1 and Type 2 MERGE helpers for Gold dimension tables.

Type 1 — overwrite changed attributes in-place (no history kept).
Type 2 — close the current row and insert a new one, preserving full history.

Both helpers use the Delta Lake MERGE (DeltaTable.merge) API so they are
safe to call incrementally on large tables.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from delta.tables import DeltaTable
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

# Sentinel for "row is still current" in SCD2 tables.
_SCD2_OPEN_END = "9999-12-31"


# ── SCD Type 1 ────────────────────────────────────────────────────────────────


def merge_scd1(
    spark: SparkSession,
    source_df: DataFrame,
    target_path: str,
    business_key: str | list[str],
    update_cols: list[str],
) -> None:
    """UPSERT *source_df* into the SCD1 Delta table at *target_path*.

    Rows matching on *business_key* are updated in-place; new rows are
    inserted.  No history is preserved.

    Parameters
    ----------
    spark:
        Active SparkSession.
    source_df:
        Incremental records to merge in.
    target_path:
        Delta table path (local dir or abfss URI).
    business_key:
        Column name(s) that uniquely identify a dimension member.
    update_cols:
        Attribute columns to update when a match is found.
    """
    keys = [business_key] if isinstance(business_key, str) else business_key

    # Ensure the target table exists; create it from source if first run.
    try:
        target = DeltaTable.forPath(spark, target_path)
    except Exception:
        source_df.write.format("delta").mode("overwrite").save(target_path)
        return

    join_cond = " AND ".join(f"target.{k} = source.{k}" for k in keys)
    set_map = {col: f"source.{col}" for col in update_cols}

    (
        target.alias("target")
        .merge(source_df.alias("source"), join_cond)
        .whenMatchedUpdate(set=set_map)
        .whenNotMatchedInsertAll()
        .execute()
    )


# ── SCD Type 2 ────────────────────────────────────────────────────────────────


def merge_scd2(
    spark: SparkSession,
    source_df: DataFrame,
    target_path: str,
    business_key: str | list[str],
    track_cols: list[str],
) -> None:
    """Slowly-changing dimension Type 2 MERGE into *target_path*.

    For each incoming row:
    - If the business key is new → INSERT with valid_from=now, valid_to=9999-12-31, is_current=True.
    - If the business key exists and any *track_cols* value differs → CLOSE the existing current
      row (set valid_to=now, is_current=False) then INSERT a new current row.
    - If nothing changed → no-op (whenNotMatchedBySourceDelete is NOT applied; this is an
      incremental insert, not a full-refresh sync).

    Parameters
    ----------
    spark:
        Active SparkSession.
    source_df:
        Incremental records to merge in.
    target_path:
        Delta table path.
    business_key:
        Column(s) that uniquely identify a dimension member.
    track_cols:
        Attribute columns whose changes trigger a new SCD2 version.
    """
    keys = [business_key] if isinstance(business_key, str) else business_key
    now = datetime.now(tz=timezone.utc).isoformat()

    # Build change-detection expression: any tracked column differs.
    change_expr = " OR ".join(
        f"target.{col} <> source.{col} OR "
        f"(target.{col} IS NULL AND source.{col} IS NOT NULL) OR "
        f"(target.{col} IS NOT NULL AND source.{col} IS NULL)"
        for col in track_cols
    )

    try:
        target = DeltaTable.forPath(spark, target_path)
    except Exception:
        # First run — initialise the table with SCD2 metadata columns.
        init_df = (
            source_df
            .withColumn("valid_from", F.lit(now))
            .withColumn("valid_to", F.lit(_SCD2_OPEN_END))
            .withColumn("is_current", F.lit(True))
        )
        init_df.write.format("delta").mode("overwrite").save(target_path)
        return

    join_cond = " AND ".join(f"target.{k} = source.{k}" for k in keys)
    is_current_and_changed = f"target.is_current = true AND ({change_expr})"

    # Step 1 — close changed current rows.
    (
        target.alias("target")
        .merge(source_df.alias("source"), f"{join_cond} AND {is_current_and_changed}")
        .whenMatchedUpdate(
            set={
                "valid_to": F.lit(now),
                "is_current": F.lit(False),
            }
        )
        .execute()
    )

    # Step 2 — insert new current rows for changed + genuinely new keys.
    existing_current = (
        DeltaTable.forPath(spark, target_path)
        .toDF()
        .filter(F.col("is_current") == True)
        .select(*keys)
    )

    # Rows that are new OR whose key just had its current row closed.
    closed_keys = (
        DeltaTable.forPath(spark, target_path)
        .toDF()
        .filter((F.col("is_current") == False) & (F.col("valid_to") == now))
        .select(*keys)
    )

    new_or_changed = source_df.join(
        existing_current, on=keys, how="left_anti"
    )

    insert_df = (
        new_or_changed
        .withColumn("valid_from", F.lit(now))
        .withColumn("valid_to", F.lit(_SCD2_OPEN_END))
        .withColumn("is_current", F.lit(True))
    )

    if insert_df.count() > 0:
        insert_df.write.format("delta").mode("append").save(target_path)
