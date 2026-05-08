"""Read Bronze NDJSON with strict schema enforcement.

Unknown-column handling: PERMISSIVE mode lets Spark parse what it can; rows
that fail entirely land in the synthetic _corrupt_record column and are caught
by the no_corrupt_record Bronze validation rule.
"""

from __future__ import annotations

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql import types as T

# ── Schemas ───────────────────────────────────────────────────────────────────

SALES_SCHEMA = T.StructType(
    [
        T.StructField("order_id", T.StringType(), nullable=True),
        T.StructField("customer_id", T.StringType(), nullable=True),
        T.StructField("product_id", T.StringType(), nullable=True),
        T.StructField("quantity", T.LongType(), nullable=True),
        T.StructField("unit_price", T.DoubleType(), nullable=True),
        T.StructField("amount", T.DoubleType(), nullable=True),
        T.StructField("status", T.StringType(), nullable=True),
        T.StructField("order_date", T.StringType(), nullable=True),
        T.StructField("ingested_at", T.StringType(), nullable=True),
        # Synthetic column: populated when Spark cannot parse a row.
        T.StructField("_corrupt_record", T.StringType(), nullable=True),
    ]
)

INVENTORY_SCHEMA = T.StructType(
    [
        T.StructField("product_id", T.StringType(), nullable=True),
        T.StructField("sku", T.StringType(), nullable=True),
        T.StructField("name", T.StringType(), nullable=True),
        T.StructField("category", T.StringType(), nullable=True),
        T.StructField("stock_qty", T.LongType(), nullable=True),
        T.StructField("reorder_level", T.LongType(), nullable=True),
        T.StructField("unit_cost", T.DoubleType(), nullable=True),
        T.StructField("last_updated", T.StringType(), nullable=True),
        T.StructField("ingested_at", T.StringType(), nullable=True),
        T.StructField("_corrupt_record", T.StringType(), nullable=True),
    ]
)

SOURCE_SCHEMAS: dict[str, T.StructType] = {
    "sales": SALES_SCHEMA,
    "inventory": INVENTORY_SCHEMA,
}

# ── Reader ────────────────────────────────────────────────────────────────────


def read_bronze(
    spark: SparkSession,
    source: str,
    date: str,
    bronze_base_path: str,
) -> DataFrame:
    """Read a single day's Bronze NDJSON partition and attach metadata columns.

    Parameters
    ----------
    spark:
        Active SparkSession.
    source:
        Source name, e.g. ``"sales"`` or ``"inventory"``.
    date:
        ISO-8601 date string, e.g. ``"2024-01-15"``.
    bronze_base_path:
        Root path of the bronze container (local dir or abfss URI).

    Returns
    -------
    DataFrame with all source columns plus:
    - ``_id``           monotonically increasing row id (required by validation runner)
    - ``_source``       literal source name
    - ``_date``         literal processing date
    - ``_bronze_path``  literal file path read
    """
    if source not in SOURCE_SCHEMAS:
        raise ValueError(
            f"Unknown source '{source}'. Add it to SOURCE_SCHEMAS in schema_enforcement.py."
        )

    schema = SOURCE_SCHEMAS[source]
    path = f"{bronze_base_path.rstrip('/')}/{source}/{date}/"

    df = (
        spark.read.schema(schema)
        .option("mode", "PERMISSIVE")
        .option("columnNameOfCorruptRecord", "_corrupt_record")
        .json(path)
    )

    return (
        df.withColumn("_id", F.monotonically_increasing_id())
        .withColumn("_source", F.lit(source))
        .withColumn("_date", F.lit(date))
        .withColumn("_bronze_path", F.lit(path))
    )
