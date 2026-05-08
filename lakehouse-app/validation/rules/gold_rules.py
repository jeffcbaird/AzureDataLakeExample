"""Validation rules applied to Gold-tier data.

Gold rules guard against business-logic violations that slip through Silver
validation — e.g. referential integrity issues or aggregation anomalies that
are only detectable once dimension and fact data have been joined.
"""

from pyspark.sql import functions as F

from lakehouse_common.validation.base_rule import Severity, ValidationRule

# ── Sales (fact_orders input) Gold rules ──────────────────────────────────────

SALES_GOLD_RULES: list[ValidationRule] = [
    ValidationRule(
        name="non_negative_amount",
        severity=Severity.ERROR,
        check=lambda df: df.filter(
            F.col("amount").isNull() | (F.col("amount").cast("double") < 0)
        ),
        description="Amount must be non-negative before writing to Gold.",
        tags=["numeric", "gold"],
    ),
    ValidationRule(
        name="valid_order_date",
        severity=Severity.ERROR,
        check=lambda df: df.filter(F.col("order_date").isNull()),
        description="order_date must be present — fact rows without a date cannot be partitioned.",
        tags=["temporal", "gold"],
    ),
    ValidationRule(
        name="known_status",
        severity=Severity.WARNING,
        check=lambda df: df.filter(
            ~F.col("status").isin(
                "pending", "processing", "shipped", "delivered", "cancelled"
            )
        ),
        description="status should be a known order-status value at Gold write time.",
        tags=["enum", "gold"],
    ),
]

# ── Inventory (dim_product input) Gold rules ──────────────────────────────────

INVENTORY_GOLD_RULES: list[ValidationRule] = [
    ValidationRule(
        name="non_negative_unit_cost",
        severity=Severity.ERROR,
        check=lambda df: df.filter(
            F.col("unit_cost").isNull() | (F.col("unit_cost").cast("double") < 0)
        ),
        description="unit_cost must be non-negative for Gold dimension rows.",
        tags=["numeric", "gold"],
    ),
    ValidationRule(
        name="non_null_sku_gold",
        severity=Severity.ERROR,
        check=lambda df: df.filter(F.col("sku").isNull() | (F.trim(F.col("sku")) == "")),
        description="sku must be present on every Gold inventory row.",
        tags=["nullability", "gold"],
    ),
]

# ── Lookup ────────────────────────────────────────────────────────────────────

_GOLD_RULES_BY_SOURCE: dict[str, list[ValidationRule]] = {
    "sales": SALES_GOLD_RULES,
    "inventory": INVENTORY_GOLD_RULES,
}


def get_gold_rules(source: str) -> list[ValidationRule]:
    """Return the Gold rule set for *source*. Returns [] for unknown sources."""
    return _GOLD_RULES_BY_SOURCE.get(source, [])
