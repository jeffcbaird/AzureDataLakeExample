"""Validation rules applied to Bronze (raw) data before Silver promotion."""

from pyspark.sql import functions as F

from lakehouse_common.validation.base_rule import Severity, ValidationRule

# ── Common rules applied to every Bronze table ────────────────────────────────

COMMON_BRONZE_RULES: list[ValidationRule] = [
    ValidationRule(
        name="no_corrupt_record",
        severity=Severity.ERROR,
        check=lambda df: df.filter(F.col("_corrupt_record").isNotNull()),
        description="Rows that Spark could not parse land in _corrupt_record.",
        tags=["schema"],
    ),
]

# ── Sales-specific Bronze rules ───────────────────────────────────────────────

SALES_BRONZE_RULES: list[ValidationRule] = [
    ValidationRule(
        name="no_null_order_id",
        severity=Severity.ERROR,
        check=lambda df: df.filter(F.col("order_id").isNull()),
        description="order_id must never be null — it is the primary business key.",
        tags=["nullability", "key"],
    ),
    ValidationRule(
        name="positive_unit_price",
        severity=Severity.ERROR,
        check=lambda df: df.filter(
            F.col("unit_price").cast("double").isNull()
            | (F.col("unit_price").cast("double") <= 0)
        ),
        description="unit_price must be a positive number.",
        tags=["numeric"],
    ),
    ValidationRule(
        name="valid_status",
        severity=Severity.WARNING,
        check=lambda df: df.filter(
            ~F.col("status").isin("pending", "processing", "shipped", "delivered", "cancelled")
        ),
        description="status should be one of the known order-status values.",
        tags=["enum"],
    ),
]

# ── Inventory-specific Bronze rules ──────────────────────────────────────────

INVENTORY_BRONZE_RULES: list[ValidationRule] = [
    ValidationRule(
        name="no_null_product_id",
        severity=Severity.ERROR,
        check=lambda df: df.filter(F.col("product_id").isNull()),
        description="product_id must never be null.",
        tags=["nullability", "key"],
    ),
    ValidationRule(
        name="non_negative_stock_qty",
        severity=Severity.ERROR,
        check=lambda df: df.filter(F.col("stock_qty").cast("long") < 0),
        description="stock_qty cannot be negative.",
        tags=["numeric"],
    ),
    ValidationRule(
        name="valid_category",
        severity=Severity.WARNING,
        check=lambda df: df.filter(
            F.col("category").isNull() | (F.trim(F.col("category")) == "UNKNOWN")
        ),
        description="category should be a known non-placeholder value.",
        tags=["enum"],
    ),
]

# ── Lookup by source name ─────────────────────────────────────────────────────

BRONZE_RULES_BY_SOURCE: dict[str, list[ValidationRule]] = {
    "sales": COMMON_BRONZE_RULES + SALES_BRONZE_RULES,
    "inventory": COMMON_BRONZE_RULES + INVENTORY_BRONZE_RULES,
}


def get_bronze_rules(source: str) -> list[ValidationRule]:
    """Return the combined Bronze rule set for *source*.

    Falls back to common rules only for unknown sources so new sources can be
    ingested without validation gaps causing pipeline failures.
    """
    return BRONZE_RULES_BY_SOURCE.get(source, COMMON_BRONZE_RULES)
