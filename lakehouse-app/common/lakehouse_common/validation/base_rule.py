"""ValidationRule and Severity dataclasses used by all Spark jobs."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from pyspark.sql import DataFrame


class Severity(Enum):
    WARNING = "WARNING"  # Row passes with _dq_flags attached
    ERROR   = "ERROR"    # Row routed to quarantine


@dataclass
class ValidationRule:
    name: str
    severity: Severity
    check: Callable[["DataFrame"], "DataFrame"]  # returns failing rows
    description: str = ""
    tags: list[str] = field(default_factory=list)

    def __repr__(self) -> str:
        return f"ValidationRule(name={self.name!r}, severity={self.severity.value})"
