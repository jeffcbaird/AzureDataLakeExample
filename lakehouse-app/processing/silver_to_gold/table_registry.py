"""_table_registry writer.

Every Gold table writes a single-row entry to silver/_table_registry/ after
each successful run, giving data consumers an at-a-glance view of table
freshness, ownership, and SLA status.

Schema
------
table_name          string   — qualified Gold table name, e.g. "fact_orders"
owner_team          string   — team responsible for the table
last_refreshed_at   timestamp
row_count           long
sla_by_utc          string   — ISO time string when the table should be ready, e.g. "06:00"
description         string
"""

from __future__ import annotations

from datetime import datetime, timezone

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import types as T

_REGISTRY_SCHEMA = T.StructType(
    [
        T.StructField("table_name", T.StringType(), False),
        T.StructField("owner_team", T.StringType(), True),
        T.StructField("last_refreshed_at", T.TimestampType(), True),
        T.StructField("row_count", T.LongType(), True),
        T.StructField("sla_by_utc", T.StringType(), True),
        T.StructField("description", T.StringType(), True),
    ]
)


def write_registry_entry(
    spark: SparkSession,
    registry_path: str,
    table_name: str,
    row_count: int,
    owner_team: str = "data-engineering",
    sla_by_utc: str = "06:00",
    description: str = "",
) -> None:
    """Append (or overwrite) a single registry row for *table_name*.

    Uses ``replaceWhere`` so only the row for *table_name* is replaced,
    leaving all other registry entries untouched.
    """
    now = datetime.now(tz=timezone.utc).replace(tzinfo=None)

    row = [(table_name, owner_team, now, row_count, sla_by_utc, description)]
    df = spark.createDataFrame(row, schema=_REGISTRY_SCHEMA)

    (
        df.write.format("delta")
        .mode("overwrite")
        .option("replaceWhere", f"table_name = '{table_name}'")
        .save(registry_path)
    )
