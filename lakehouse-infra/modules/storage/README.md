# module: storage

Provisions the ADLS Gen2 storage account and the four lakehouse containers.

## Resources

| Resource | Name pattern | Notes |
|---|---|---|
| `azurerm_storage_account` | `st{project}{env}adls` | HNS enabled, LRS, TLS 1.2, soft-delete |
| `azurerm_storage_data_lake_gen2_filesystem` | `bronze` | Raw ingest landing zone |
| `azurerm_storage_data_lake_gen2_filesystem` | `silver` | Cleansed Delta tables |
| `azurerm_storage_data_lake_gen2_filesystem` | `gold` | Curated Delta tables |
| `azurerm_storage_data_lake_gen2_filesystem` | `quarantine` | Rows that failed ERROR-severity validation rules |
| `azurerm_storage_management_policy` | — | Moves `bronze/` blobs to cool tier after 90 days |
| `azurerm_monitor_diagnostic_setting` | — | Enabled when `log_analytics_workspace_id` is provided (Phase 4) |

## Managed Delta table paths

The following paths within the `silver` container are reserved and managed exclusively by the
Spark jobs. **Do not create or delete these paths manually.**

| Path | Purpose | Owner |
|---|---|---|
| `silver/dq_results/` | Validation run results — one row per rule per job run. Schema: `run_id, table_name, rule_name, severity, passed, failing_count, run_timestamp` | Bronze→Silver Spark job (first write creates the table) |
| `silver/_table_registry/` | Gold table metadata — freshness, SLA, owner team, row count. Schema: `table_name, owner_team, last_refreshed_at, row_count, sla_by_utc, description` | Silver→Gold Spark job (first write creates the table) |

These paths are exposed as Terraform outputs (`dq_results_abfss_uri`, `table_registry_abfss_uri`)
and as constants in `lakehouse_common/config/paths.py` so all Spark jobs reference them
consistently without hardcoding.

## Outputs

| Output | Description |
|---|---|
| `storage_account_name` | Storage account name |
| `storage_account_id` | Resource ID |
| `adls_primary_dfs_endpoint` | Primary DFS endpoint URL |
| `bronze_abfss_uri` | `abfss://bronze@<account>.dfs.core.windows.net` |
| `silver_abfss_uri` | `abfss://silver@<account>.dfs.core.windows.net` |
| `gold_abfss_uri` | `abfss://gold@<account>.dfs.core.windows.net` |
| `quarantine_abfss_uri` | `abfss://quarantine@<account>.dfs.core.windows.net` |
| `dq_results_abfss_uri` | Full URI to `silver/dq_results/` |
| `table_registry_abfss_uri` | Full URI to `silver/_table_registry/` |
| `{bronze,silver,gold,quarantine}_filesystem_id` | Filesystem resource IDs |

## Phase gate

After applying this module against `dev`, verify:
- All four containers exist in the Azure portal.
- The lifecycle rule is visible on the `bronze` container under **Data management → Lifecycle management**.
- `terraform plan` is clean (no pending changes).
