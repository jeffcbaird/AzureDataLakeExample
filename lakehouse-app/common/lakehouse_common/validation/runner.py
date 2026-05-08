"""
run_validation() — applies a list of ValidationRules to a DataFrame.

Returns:
    clean_df      — rows that passed all ERROR rules (may have _dq_flags for WARNINGs)
    quarantine_df — rows that failed at least one ERROR rule, with _rule_name attached
    dq_results_df — one summary row per rule: run_id, rule_name, severity, passed,
                    failing_count, run_timestamp
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Sequence

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

from lakehouse_common.validation.base_rule import Severity, ValidationRule


def run_validation(
    df: DataFrame,
    rules: Sequence[ValidationRule],
    table_name: str,
    spark: SparkSession | None = None,
) -> tuple[DataFrame, DataFrame, DataFrame]:
    spark = spark or df.sparkSession

    run_id        = str(uuid.uuid4())
    run_timestamp = datetime.now(timezone.utc).isoformat()

    clean_df      = df
    quarantine_df = spark.createDataFrame([], df.schema)
    dq_rows: list[dict] = []

    for rule in rules:
        failing = rule.check(clean_df)
        failing_count = failing.count()
        passed = failing_count == 0

        dq_rows.append({
            "run_id":        run_id,
            "table_name":    table_name,
            "rule_name":     rule.name,
            "severity":      rule.severity.value,
            "passed":        passed,
            "failing_count": failing_count,
            "run_timestamp": run_timestamp,
        })

        if not passed:
            if rule.severity == Severity.ERROR:
                failing_tagged = failing.withColumn("_rule_name", F.lit(rule.name))
                quarantine_df  = quarantine_df.unionByName(failing_tagged, allowMissingColumns=True)
                # Remove failing rows from clean set
                clean_df = clean_df.subtract(failing)
            else:
                # WARNING — attach flag but keep the row
                flag_col = F.when(
                    F.col("_dq_flags").isNull(), F.array(F.lit(rule.name))
                ).otherwise(F.array_append(F.col("_dq_flags"), F.lit(rule.name)))

                if "_dq_flags" not in clean_df.columns:
                    clean_df = clean_df.withColumn("_dq_flags", F.lit(None).cast("array<string>"))
                clean_df = clean_df.withColumn(
                    "_dq_flags",
                    F.when(
                        F.col("_id").isin([r["_id"] for r in failing.select("_id").collect()]),
                        flag_col,
                    ).otherwise(F.col("_dq_flags")),
                )

    schema = "run_id string, table_name string, rule_name string, severity string, " \
             "passed boolean, failing_count long, run_timestamp string"
    dq_results_df = spark.createDataFrame(dq_rows, schema=schema)

    return clean_df, quarantine_df, dq_results_df
