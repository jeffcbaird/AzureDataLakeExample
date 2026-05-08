"""Bronze → Silver processing job.

Entry point for both local development (``python -m processing.bronze_to_silver.job``)
and Synapse Spark Job Definition execution.

Environment variables
---------------------
SOURCE      Source name, e.g. ``sales`` or ``inventory``.  Required.
DATE        ISO-8601 processing date, e.g. ``2024-01-15``.  Required.
ENV         Runtime environment: ``local`` (default) or ``azure``.

When ENV=local the Settings class resolves paths to the local data directory;
when ENV=azure it resolves to abfss:// URIs backed by ADLS Gen2.
"""

from __future__ import annotations

import os
import sys

from pyspark.sql import SparkSession

from lakehouse_common.config.settings import Settings
from lakehouse_common.validation.runner import run_validation

from .deduplication import deduplicate
from .normalization import normalize
from .quarantine import write_quarantine
from .schema_enforcement import read_bronze
from validation.rules.bronze_rules import get_bronze_rules
from validation.rules.silver_rules import get_silver_rules


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise EnvironmentError(f"Required environment variable '{name}' is not set.")
    return value


def run(source: str, date: str) -> dict[str, int]:
    """Execute the full Bronze → Silver pipeline for one source/date partition.

    Returns a summary dict with keys ``bronze_rows``, ``quarantine_rows``,
    ``silver_rows``, ``warning_rows``.
    """
    settings = Settings()

    spark = (
        SparkSession.builder.appName(f"bronze_to_silver_{source}_{date}")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config(
            "spark.sql.catalog.spark_catalog",
            "org.apache.spark.sql.delta.catalog.DeltaCatalog",
        )
        .getOrCreate()
    )

    # ── 1. Read ───────────────────────────────────────────────────────────────
    bronze_df = read_bronze(spark, source, date, settings.bronze_path())
    bronze_count = bronze_df.count()

    # ── 2. Bronze validation ──────────────────────────────────────────────────
    bronze_rules = get_bronze_rules(source)
    clean_df, quarantine_df, dq_bronze_df = run_validation(
        bronze_df, bronze_rules, table_name=f"bronze_{source}", spark=spark
    )

    quarantine_count = write_quarantine(quarantine_df, settings.quarantine_path())

    # ── 3. Normalize ──────────────────────────────────────────────────────────
    normalized_df = normalize(clean_df, source)

    # ── 4. Deduplicate ────────────────────────────────────────────────────────
    deduped_df = deduplicate(normalized_df, source)

    # ── 5. Silver validation ──────────────────────────────────────────────────
    silver_rules = get_silver_rules(source)
    silver_df, silver_quarantine_df, dq_silver_df = run_validation(
        deduped_df, silver_rules, table_name=f"silver_{source}", spark=spark
    )

    # Silver-level quarantine goes to the same table with a different _source tag.
    silver_quarantine_df = silver_quarantine_df.withColumn(
        "_source", silver_quarantine_df["_source"]
    )
    write_quarantine(silver_quarantine_df, settings.quarantine_path())

    # ── 6. Write Silver (Delta, partition-scoped replace) ─────────────────────
    silver_path = settings.silver_path(source)
    # Drop internal metadata columns before writing to Silver.
    output_df = silver_df.drop("_id", "_bronze_path")

    (
        output_df.write.format("delta")
        .mode("overwrite")
        .option("replaceWhere", f"_date = '{date}'")
        .partitionBy("_date")
        .save(silver_path)
    )

    # ── 7. Persist DQ results ─────────────────────────────────────────────────
    dq_all = dq_bronze_df.unionByName(dq_silver_df)
    (
        dq_all.write.format("delta")
        .mode("append")
        .save(settings.dq_results_path())
    )

    silver_count = output_df.count()

    spark.stop()

    return {
        "bronze_rows": bronze_count,
        "quarantine_rows": quarantine_count,
        "silver_rows": silver_count,
    }


if __name__ == "__main__":
    source = _require_env("SOURCE")
    date = _require_env("DATE")
    summary = run(source, date)
    print(f"bronze_to_silver complete: {summary}")
    sys.exit(0)
