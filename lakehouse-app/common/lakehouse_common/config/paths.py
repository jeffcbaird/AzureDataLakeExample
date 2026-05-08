"""Managed path constants — used by Spark jobs to reference reserved Delta table locations."""
from lakehouse_common.config.settings import Settings

_s = Settings()

DQ_RESULTS_PATH    = _s.dq_results_path()
TABLE_REGISTRY_PATH = _s.table_registry_path()
