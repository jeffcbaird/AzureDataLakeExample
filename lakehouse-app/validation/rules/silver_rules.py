"""Validation rules applied to Silver (cleansed) data after normalization."""

from pyspark.sql import functions as F

from lakehouse_common.validation.base_rule import Severity, ValidationRule

# ── Sales Silver rules ────────────────────────────────────────────────────────

SALES_SILVER_RULES: list[ValidationRule] = [
    ValidationRule(
        name="no_null_order_date",
        severity=Severity.ERROR,
        check=lambda df: df.filter(F.col("order_date").isNull()),
        description="order_date must be present on every Silver sales row.",
        tags=["nullability", "temporal"],
    ),
    ValidationRule(
        name="positive_amount",
        severity=Severity.ERROR,
        check=lambda df: df.filter(
            F.col("amount").isNull() | (F.col("amount").cast("double") <= 0)
        ),
        description="amount must be a positive number.",
        tags=["numeric"],
    ),
    ValidationRule(
        name="quantity_at_least_one",
        severity=Severity.WARNING,
        check=lambda df: df.filter(
            F.col("quantity").cast("long").isNull() | (F.col("quantity").cast("long") < 1)
        ),
        description="quantity should be ≥ 1 for a valid order line.",
        tags=["numeric"],
    ),
]

# ── Inventory Silver rules ────────────────────────────────────────────────────

INVENTORY_SILVER_RULES: list[ValidationRule] = [
    ValidationRule(
        name="no_null_sku",
        severity=Severity.ERROR,
        check=lambda df: df.filter(F.col("sku").isNull() | (F.trim(F.col("sku")) == "")),
        description="sku must be present on every Silver inventory row.",
        tags=["nullability", "key"],
    ),
    ValidationRule(
        name="positive_unit_cost",
        severity=Severity.ERROR,
        check=lambda df: df.filter(
            F.col("unit_cost").isNull() | (F.col("unit_cost").cast("double") <= 0)
        ),
        description="unit_cost must be a positive number.",
        tags=["numeric"],
    ),
    ValidationRule(
        name="reorder_level_positive",
        severity=Severity.WARNING,
        check=lambda df: df.filter(
            F.col("reorder_level").cast("long").isNull()
            | (F.col("reorder_level").cast("long") < 0)
        ),
        description="reorder_level should be non-negative.",
        tags=["numeric"],
    ),
]

# ── Lookup by source name ─────────────────────────────────────────────────────

SILVER_RULES_BY_SOURCE: dict[str, list[ValidationRule]] = {
    "sales": SALES_SILVER_RULES,
    "inventory": INVENTORY_SILVER_RULES,
}


def get_silver_rules(source: str) -> list[ValidationRule]:
    """Return the Silver rule set for *source*.  Returns [] for unknown sources."""
    return SILVER_RULES_BY_SOURCE.get(source, [])
