"""
ENV-aware path resolver.

When ENV=local  → returns local filesystem paths under LOCAL_DATA_ROOT.
When ENV=azure  → returns ADLS Gen2 abfss:// URIs.

Usage:
    from lakehouse_common.config.settings import Settings
    s = Settings()
    bronze_path = s.bronze_path("sales")   # data/local/bronze/sales  OR  abfss://bronze@...
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Settings:
    env: str = field(default_factory=lambda: os.getenv("ENV", "local"))
    local_data_root: str = field(default_factory=lambda: os.getenv("LOCAL_DATA_ROOT", "./data/local"))
    adls_account_name: str = field(default_factory=lambda: os.getenv("ADLS_ACCOUNT_NAME", ""))
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))

    # ── Path helpers ──────────────────────────────────────────────────────────

    def _local(self, container: str, *parts: str) -> str:
        return str(Path(self.local_data_root) / container / Path(*parts) if parts else Path(self.local_data_root) / container)

    def _abfss(self, container: str, *parts: str) -> str:
        base = f"abfss://{container}@{self.adls_account_name}.dfs.core.windows.net"
        return "/".join([base] + list(parts)) if parts else base

    def _path(self, container: str, *parts: str) -> str:
        if self.is_local:
            return self._local(container, *parts)
        return self._abfss(container, *parts)

    # ── Public API ────────────────────────────────────────────────────────────

    @property
    def is_local(self) -> bool:
        return self.env == "local"

    @property
    def is_azure(self) -> bool:
        return self.env == "azure"

    def bronze_path(self, source: str = "") -> str:
        return self._path("bronze", source) if source else self._path("bronze")

    def silver_path(self, source: str = "") -> str:
        return self._path("silver", source) if source else self._path("silver")

    def gold_path(self, table: str = "") -> str:
        return self._path("gold", table) if table else self._path("gold")

    def quarantine_path(self, source: str = "") -> str:
        return self._path("quarantine", source) if source else self._path("quarantine")

    def dq_results_path(self) -> str:
        return self._path("silver", "dq_results")

    def table_registry_path(self) -> str:
        return self._path("silver", "_table_registry")
