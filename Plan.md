# Azure Data Lakehouse — Implementation Plan

> **⚠ Example Project — $1/month Azure spend cap**
>
> This is a reference/demonstration project. All Azure resources must remain within a **hard
> budget of $1 USD per month**. Resources that would exceed this limit must be fully defined in
> Terraform and application code (so the architecture is demonstrable) but **must not be
> provisioned** in any live Azure subscription. See the
> [Example Project Budget Constraint](#example-project-budget-constraint) section for the
> complete list of what to deploy vs. what to keep as code-only.

## Overview

This document is the authoritative implementation plan for an Azure data lakehouse that ingests
from 50 third-party APIs and FTP servers (~2GB/day), processes data through Bronze → Silver → Gold
tiers, and serves business intelligence via Power BI. The architecture prioritises Infrastructure
as Code (IaC) with Terraform, cost efficiency, and developer experience including full local
execution support.

---

## Repository Structure

All work lives across two repositories in Azure DevOps:

| Repository | Purpose |
|---|---|
| `lakehouse-infra` | Terraform infrastructure — all Azure resources |
| `lakehouse-app` | Application code — Spark jobs, Functions, AAS model, SQL, tests |

### `lakehouse-infra` structure

```
lakehouse-infra/
├── backend.tf                            # Remote state → Azure Storage Account (manual bootstrap)
├── main.tf                               # Root module — wires sub-modules
├── variables.tf
├── outputs.tf
├── terraform.tfvars.example
├── .terraform.lock.hcl
├── environments/
│   ├── dev.tfvars
│   └── prod.tfvars
├── modules/
│   ├── storage/                          # ADLS Gen2, containers, lifecycle rules
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── key_vault/                        # Key Vault, RBAC, access policies
│   ├── data_factory/                     # ADF instance, Git config, linked services, IRs
│   ├── functions/                        # Function app, consumption plan, app settings
│   ├── synapse/                          # Workspace, Spark pool, Serverless SQL firewall
│   │   ├── main.tf
│   │   ├── spark_requirements.txt        # lakehouse-common[spark] version pin
│   │   └── variables.tf
│   ├── analysis_services/                # AAS server, firewall rules, admin users
│   └── monitoring/                       # Log Analytics, Monitor alerts, Workbook
│       ├── main.tf
│       ├── workbook.json                 # Azure Monitor Workbook definition (parameterised)
│       └── variables.tf
└── pipelines/
    ├── tf-plan.yml                       # Runs on PR → terraform plan
    └── tf-apply.yml                      # Runs on merge to main → terraform apply
```

### `lakehouse-app` structure

```
lakehouse-app/
├── README.md
├── Makefile
├── docker-compose.yml
├── pip.ini                               # Azure Artifacts feed config (no credentials)
├── .env.example
│
├── common/                               # Shared Python package → published to Azure Artifacts
│   ├── pyproject.toml
│   └── lakehouse_common/
│       ├── __init__.py
│       ├── config/
│       │   └── settings.py               # ENV-aware path resolution (local vs Azure)
│       ├── clients/
│       │   ├── base_http.py              # Retry, pagination, auth base class
│       │   └── base_ftp.py               # FTP/SFTP base client
│       ├── keyvault/
│       │   └── client.py                 # get_secret(), list_secrets()
│       ├── logging/
│       │   └── structured.py             # JSON-structured logger for Log Analytics
│       └── validation/
│           ├── base_rule.py              # ValidationRule, Severity dataclasses
│           └── runner.py                 # run_validation() — used by all Spark jobs
│
├── ingestion/                            # Azure Functions — deployed as one Function App
│   ├── shared/                           # Function-app-local utilities (not packaged)
│   │   ├── keyvault.py
│   │   └── logging.py
│   ├── api/
│   │   ├── clients/                      # One module per source API
│   │   │   ├── sales_client.py
│   │   │   └── inventory_client.py
│   │   └── function_app.py
│   ├── ftp/
│   │   └── function_app.py
│   ├── host.json
│   └── requirements.txt                  # lakehouse-common>=x.x.x, azure-functions
│
├── processing/
│   ├── bronze_to_silver/
│   │   ├── job.py                        # spark-submit entry point
│   │   ├── schema_enforcement.py
│   │   ├── deduplication.py
│   │   ├── normalization.py
│   │   └── quarantine.py
│   ├── silver_to_gold/
│   │   ├── job.py
│   │   ├── dimensions.py                 # SCD Type 1 + 2 MERGE logic
│   │   ├── facts.py
│   │   └── metrics.py
│   └── requirements.txt                  # lakehouse-common[spark]>=x.x.x
│
├── validation/
│   └── rules/
│       ├── bronze_rules.py
│       ├── silver_rules.py
│       └── gold_rules.py
│
├── monitoring/
│   ├── canary.py                         # Per-source connectivity pings
│   └── heartbeat.py                      # Writes heartbeat record to Delta
│
├── sql/
│   ├── serverless/
│   │   ├── external_tables/              # DDL pointing at Gold Delta paths on ADLS
│   │   └── views/                        # Business-friendly views for Power BI
│   └── gold/
│       └── constraints.sql               # Delta CONSTRAINTS on Gold tables
│
├── adf/                                  # Deployed via ADF Git integration
│   ├── pipeline/
│   ├── dataset/
│   ├── linkedService/
│   └── trigger/
│
├── aas/
│   └── model.bim                         # TMSL tabular model definition
│
├── scripts/
│   ├── seed_local_data.py                # Generates sample CSVs for local dev
│   └── reset_local_lakehouse.py          # Wipes local /mnt/lakehouse for clean run
│
├── tests/
│   ├── unit/
│   │   ├── test_schema_enforcement.py
│   │   ├── test_deduplication.py
│   │   ├── test_normalization.py
│   │   └── test_validation_rules.py
│   ├── integration/                      # Scheduled every 15 min in Azure DevOps
│   │   ├── test_api_health.py
│   │   └── test_ftp_health.py
│   └── conftest.py
│
└── pipelines/                            # Azure DevOps CI/CD definitions
    ├── publish-common.yml                # Triggers on common/ changes → Azure Artifacts
    ├── deploy-functions.yml
    ├── deploy-spark-jobs.yml
    ├── deploy-aas-model.yml
    ├── deploy-sql-scripts.yml
    ├── deploy-powerbi.yml                # Power BI REST API workspace + dataset
    └── run-integration-tests.yml         # Scheduled every 15 min
```

---

## Local Development Environment

Engineers must be able to run all Spark jobs locally without Azure credentials. Docker Compose
provides a PySpark environment with a local filesystem standing in for ADLS Gen2.

```
git clone lakehouse-app && cd lakehouse-app
cp .env.example .env          # local values only — no Azure credentials needed
make install                  # editable install of lakehouse-common
make up                       # starts Docker Compose PySpark + Jupyter container
make seed                     # generates sample CSVs in data/local/bronze/
make bronze-silver            # runs Bronze→Silver Spark job locally
make silver-gold              # runs Silver→Gold Spark job locally
make test                     # runs unit tests (no Spark cluster required)
make lint                     # runs ruff
```

The `config/settings.py` in `lakehouse_common` switches all paths based on the `ENV` environment
variable (`local` vs `azure`). No job code changes between environments.

### Common package — local editable install

```bash
pip install -e ./common                   # changes to lakehouse_common/ reflected immediately
pip install "lakehouse-common[spark]"     # Spark environments
pip install "lakehouse-common"            # Functions and tests
```

The package is published to an **Azure Artifacts** private PyPI feed on every merge to `main`
that touches `common/`. All Function Apps and Synapse Spark pools install from this feed.
Version bumps are manual in `pyproject.toml` and must accompany PRs that change the package.

---

## Implementation Phases

---

### Phase 0 — Foundation & Developer Environment

**Terraform repo:** `lakehouse-infra` (bootstrap only — manual one-time actions)
**App repo:** `lakehouse-app` (structure and local dev)

#### Actions

1. Create both repositories in Azure DevOps with branch protection on `main`.
2. Manually create an Azure Storage Account and container for Terraform remote state. Commit
   `backend.tf` referencing it. This is the only manual Azure resource in the entire project.
3. Create three Azure DevOps pipeline definitions (no stages will run yet):
   - `tf-plan.yml` — triggers on PR to `lakehouse-infra`
   - `tf-apply.yml` — triggers on merge to `lakehouse-infra` main
   - `run-integration-tests.yml` — scheduled every 15 minutes against `lakehouse-app` main
4. Scaffold the full directory structures for both repositories.
5. Configure `pip.ini` with the Azure Artifacts feed URL (no credentials — injected by pipeline).
6. Write `docker-compose.yml` and `Makefile` so local dev works before any Azure resources exist.
7. Write and test `scripts/seed_local_data.py` to produce realistic sample CSVs.

#### Azure resources
- Azure Storage Account (Terraform state) — manual
- Azure DevOps project, repositories, pipelines — manual

#### IaC ownership
| Resource | Owner |
|---|---|
| Terraform state storage | Manual bootstrap |
| Azure DevOps repos + pipelines | Manual |
| All subsequent resources | `lakehouse-infra` Terraform |

---

### Phase 1 — Storage Layer

**Terraform module:** `lakehouse-infra/modules/storage/`

#### Actions

1. Provision ADLS Gen2 with hierarchical namespace enabled.
2. Create four containers: `bronze`, `silver`, `gold`, `quarantine`.
3. Reserve `silver/dq_results/` and `silver/_table_registry/` as managed Delta table paths.
   Document both in `_table_registry` from first write.
4. Configure lifecycle management: move bronze files to cool tier after 90 days (raw CSVs are
   reference-only after initial processing).
5. Wire ADLS diagnostic settings to Log Analytics (provisioned in Phase 4).

#### Key Terraform resources
- `azurerm_storage_account`
- `azurerm_storage_data_lake_gen2_filesystem` (×4 — bronze, silver, gold, quarantine)
- `azurerm_storage_management_policy` (bronze cool-tier lifecycle rule)
- `azurerm_monitor_diagnostic_setting` (wired to Log Analytics)

---

### Phase 2 — Security

**Terraform module:** `lakehouse-infra/modules/key_vault/` + root RBAC assignments

#### Actions

1. Provision Key Vault with soft-delete and purge protection enabled.
2. Store all secrets in Key Vault — API keys, FTP credentials, Synapse admin password, AAS
   connection string. Secret values passed in via `tfvars` or CI pipeline secrets. Never stored
   in state.
3. Provision managed identities for all compute resources and assign RBAC roles now, before
   those resources are created. Role assignments activate when resources appear.

#### Required RBAC assignments
| Identity | Role | Scope |
|---|---|---|
| ADF managed identity | Key Vault Secrets User | Key Vault |
| ADF managed identity | Storage Blob Data Contributor | bronze, silver containers |
| Functions managed identity | Key Vault Secrets User | Key Vault |
| Functions managed identity | Storage Blob Data Contributor | bronze container |
| Synapse managed identity | Key Vault Secrets User | Key Vault |
| Synapse managed identity | Storage Blob Data Contributor | all containers + quarantine |
| AAS managed identity | Storage Blob Data Reader | gold container |
| DevOps service principal | Artifacts Contributor | Azure Artifacts feed |
| Synapse managed identity | Artifacts Reader | Azure Artifacts feed |

#### Key Terraform resources
- `azurerm_key_vault`
- `azurerm_key_vault_secret` (×n — one per credential)
- `azurerm_role_assignment` (×n — all RBAC above)

---

### Phase 3 — Ingestion

**Terraform module:** `lakehouse-infra/modules/data_factory/`, `lakehouse-infra/modules/functions/`
**DevOps pipelines:** `publish-common.yml`, `deploy-functions.yml`
**ADF Git:** `lakehouse-app/adf/`

#### Actions

1. Provision ADF instance with Git integration pointing at `lakehouse-app/adf/` in the app repo.
   ADF pipeline JSON lives in the app repo alongside the code it orchestrates.
2. Provision Azure Functions app on Consumption plan. If any FTP source consistently exceeds 10
   minutes (large file transfer), provision a second Function App on Premium plan for that source
   only — do not upgrade the entire app.
3. Create an Azure Artifacts feed named `lakehouse-feed` in Azure DevOps (manual, one-time).
4. Build ingestion clients in `lakehouse_common/clients/` with retry logic using `tenacity`,
   OAuth/API key auth, and pagination support. Source-specific clients in
   `ingestion/api/clients/`.
5. Configure the hybrid ingestion pattern: ADF schedules and retries, Functions handles IO.
   ADF calls Functions via the Azure Function activity and receives row count + file path in the
   response payload.
6. Deploy `publish-common.yml` pipeline — triggers on changes to `common/`, builds wheel, pushes
   to Azure Artifacts feed.
7. Deploy `deploy-functions.yml` pipeline — authenticates to Azure Artifacts via
   `PipAuthenticate` task, installs `requirements.txt`, publishes to Function App.
8. Activate `run-integration-tests.yml` — runs `pytest tests/integration` every 15 minutes.
   Posts failures to Teams/Slack webhook. This is the earliest warning layer for third-party API
   availability.

#### Azure resources
- `azurerm_data_factory` (with `vsts_configuration` block pointing at app repo)
- `azurerm_data_factory_linked_service_key_vault`
- `azurerm_data_factory_linked_service_azure_function`
- `azurerm_linux_function_app` (Consumption plan)
- `azurerm_service_plan` (Consumption)
- Azure Artifacts feed (manual, one-time)
- Azure DevOps self-hosted agent VM for scheduled integration tests (B1s, ~$8/month)

#### ADF pipeline files (in `lakehouse-app/adf/`)
- One trigger per source (schedule, daily)
- One pipeline per source: trigger → Function activity → status check activity
- Canary pipelines: lightweight ping per source on 15-minute schedule

#### IaC ownership split
| Component | Owner |
|---|---|
| ADF instance, Git config, linked services | `lakehouse-infra` Terraform |
| ADF pipeline JSON, datasets, triggers | `lakehouse-app/adf/` via ADF Git |
| Function App infrastructure | `lakehouse-infra` Terraform |
| Function code + deployment | `lakehouse-app` DevOps pipeline |
| Common package | `lakehouse-app` DevOps (`publish-common.yml`) |

---

### Phase 4 — Monitoring & Observability

**Terraform module:** `lakehouse-infra/modules/monitoring/`

Stand up observability before data flows. The first pipeline run should be fully instrumented.

#### Actions

1. Provision Log Analytics workspace. Wire ADF diagnostics, Functions diagnostics, and Synapse
   diagnostics to it.
2. Provision Azure Monitor alert rules for:
   - ADF pipeline failure rate exceeding 5% in a 1-hour window
   - Azure Function error rate exceeding threshold
   - Absence of expected bronze files within source-specific time windows (per-source variable)
   - Missing AAS heartbeat (Phase 7)
3. Provision the Azure Monitor Workbook from `workbook.json`. The workbook is parameterised —
   Terraform injects the Log Analytics workspace ID and Synapse Serverless endpoint at apply time,
   making it identical across environments.
4. Wire all alerts to an action group that posts to the team notification channel.

#### Monitoring dashboard panels
The workbook renders four panels:

- **KPI row** — pipeline runs today, success rate (red/amber/green), DQ pass rate, Gold
  freshness vs SLA
- **Source health table** — per source: last run time, status pill (ok/late/failed), rows loaded,
  DQ pass rate, quarantine count. Sources: ADF diagnostics (Log Analytics KQL) + `dq_results`
  Delta table (Synapse Serverless SQL, activated Phase 7)
- **DQ violations** — recent rule failures with severity (red = ERROR / amber = WARNING), row
  count, table, timestamp
- **Tier row counts** — Bronze / Silver / Gold / Quarantine with attrition ratio. Bronze→Gold
  gap is the primary signal for unexpected processing failures.

#### KQL queries (Log Analytics)
```kql
-- Pipeline success rate
ADFPipelineRun
| where TimeGenerated > ago(12h)
| summarize
    total     = count(),
    succeeded = countif(Status == "Succeeded"),
    failed    = countif(Status == "Failed")
    by bin(TimeGenerated, 1h), PipelineName
| extend success_rate = round(todouble(succeeded) / total * 100, 1)

-- Gold freshness (via Synapse Serverless linked query)
SELECT table_name, MAX(last_refreshed_at) AS last_refreshed
FROM gold._table_registry
GROUP BY table_name
ORDER BY last_refreshed DESC
```

#### Key Terraform resources
- `azurerm_log_analytics_workspace`
- `azurerm_monitor_action_group` (Teams/Slack webhook)
- `azurerm_monitor_metric_alert` (×n — one per alert rule)
- `azurerm_application_insights_workbook`
- `azurerm_monitor_diagnostic_setting` (×n — one per compute resource)

---

### Phase 5 — Bronze to Silver Processing

**Terraform module:** `lakehouse-infra/modules/synapse/`
**DevOps pipeline:** `deploy-spark-jobs.yml`

#### Actions

1. Provision Synapse Analytics workspace and Spark pool (Small nodes, auto-pause 10 minutes).
   Size the pool to process the largest single source comfortably — for 2GB/day total, a
   3-node Small cluster is sufficient.
2. Configure the Spark pool's `library_requirement` block in Terraform to install
   `lakehouse-common[spark]` from Azure Artifacts on pool startup.
3. Deploy Bronze→Silver Spark job scripts via `deploy-spark-jobs.yml`. The job sequence:

```
Read CSV from bronze (PERMISSIVE mode + explicit schema)
  ↓
Capture corrupt records → _corrupt_record column
  ↓
Apply type casting, date normalisation, string normalisation, enum mapping
  ↓
Deduplicate on business keys (window function, keep latest by ingested_at)
  ↓
Attach _row_hash (SHA-256 of business key columns)
  ↓
run_validation() → routes ERROR rows to quarantine, WARNING rows pass with _dq_flags
  ↓
Write quarantine rows → ADLS quarantine container (Delta, partitioned by source + date)
  ↓
Write clean rows → silver/source_name/ (Delta, replaceWhere on source_date partition)
  ↓
Append DQ results → silver/dq_results/ (Delta)
```

4. Trigger the job from ADF via a Synapse Spark Job Definition activity. ADF handles scheduling
   and retry — Synapse handles compute.

#### Validation framework

Rules are defined in `validation/rules/silver_rules.py` as `ValidationRule` dataclasses:

```python
ValidationRule(
    name="amount_positive_range",
    severity=Severity.ERROR,
    check=lambda df: df.filter(~col("amount").between(0, 1_000_000)),
    description="amount must be between 0 and 1,000,000",
)
```

- `ERROR` severity — row routed to quarantine, excluded from silver
- `WARNING` severity — row passes with `_dq_flags` array column attached

Results written to `dq_results` Delta table with columns:
`run_id, table_name, rule_name, severity, passed, failing_count, run_timestamp`

#### Local development workflow
```bash
make seed          # creates realistic CSVs in data/local/bronze/
make bronze-silver # runs job against local filesystem
# inspect data/local/silver/    → clean Delta output
# inspect data/local/quarantine → failed rows with rule name
# inspect data/local/dq_results → validation run results
make test          # unit tests — in-memory DataFrames, no cluster needed
```

#### Key Terraform resources
- `azurerm_synapse_workspace`
- `azurerm_synapse_spark_pool` (auto-pause, library requirements pointing at Azure Artifacts)
- `azurerm_synapse_firewall_rule`
- `azurerm_role_assignment` (Synapse MI → Storage)

---

### Phase 6 — Silver to Gold Processing

**DevOps pipeline:** `deploy-spark-jobs.yml` (same pipeline, additional job definitions)

No new Terraform resources are needed. Gold jobs deploy alongside Silver jobs.

#### Actions

1. Deploy Silver→Gold Spark job. The job sequence:

```
Load incremental silver partition (replaceWhere date window)
  ↓
Apply business rules and derived metrics
  ↓
MERGE into dimension tables (SCD Type 1 or Type 2 per dimension)
  ↓
Append / replaceWhere fact table partitions
  ↓
Recompute affected aggregation partitions
  ↓
run_validation() with gold_rules → append to dq_results
  ↓
Update _table_registry (table_name, owner, last_refreshed_at, row_count, sla_by_utc)
```

2. Use `replaceWhere` windows of 7 days on fact tables to catch late-arriving source data.
3. ADF pipeline for Gold has explicit dependencies — the Silver job for the same date partition
   must succeed before Gold starts.
4. Apply Delta CONSTRAINTS to all Gold tables (deployed via `deploy-sql-scripts.yml`):

```sql
ALTER TABLE gold.fact_orders
ADD CONSTRAINT amount_positive CHECK (amount >= 0);

ALTER TABLE gold.dim_customer
ADD CONSTRAINT customer_id_not_null CHECK (customer_id IS NOT NULL);
```

5. Populate `_table_registry` for every Gold table with `owner_team`, `sla_by_utc`, and
   `description`. Domain team ownership is established at this phase — data engineering owns the
   pipeline, domain teams own the definition of correct.

#### Gold table types produced
| Table type | Pattern | Example |
|---|---|---|
| Dimension (SCD Type 1) | MERGE on business key | `dim_product` |
| Dimension (SCD Type 2) | MERGE with history tracking | `dim_customer` |
| Fact | Append + replaceWhere | `fact_orders` |
| Pre-aggregated metrics | replaceWhere on affected date partitions | `daily_revenue_summary` |
| ML feature table | Rolling window aggregates, point-in-time safe | `customer_features` |

#### Local development workflow
```bash
make bronze-silver  # prerequisite
make silver-gold    # runs S→G job against local silver/
# inspect data/local/gold/ — verify dim/fact/metric tables
```

---

### Phase 7 — Serving Layer

**Terraform module:** `lakehouse-infra/modules/analysis_services/` (AAS server)
**DevOps pipelines:** `deploy-sql-scripts.yml`, `deploy-aas-model.yml`

#### Actions

1. Provision AAS server. Use S0 ($336/month always-on, ~$64-138/month with pause schedule)
   for production, D1 ($57/month) for dev — D1 has no SLA and is sufficient for model
   development.
2. Configure an ADF pipeline (or Azure Automation runbook) to pause AAS at 20:00 UTC and
   resume at 07:00 UTC on weekdays. This saves up to $198/month on S0 with no manual effort.
3. Deploy Synapse Serverless SQL external tables via `deploy-sql-scripts.yml`. Tables point at
   Gold Delta paths on ADLS. Business-friendly views in `sql/serverless/views/` are what Power BI
   connects to — analysts never query external tables directly.
4. Deploy AAS tabular model from `aas/model.bim` via the `AnalysisServicesProcess` DevOps task.
   Model connects to AAS using the Synapse Serverless endpoint as its source:
   `Gold Delta files → Synapse Serverless view → AAS import`
5. Configure the AAS refresh trigger in ADF — fires after Gold job completes successfully.
6. Activate the Synapse Serverless connection in the monitoring workbook. DQ violations and
   tier row count panels will populate with live data for the first time.
7. Configure firewall rules on AAS and Synapse Serverless to allow Power BI service IP ranges.

#### Key Terraform resources
- `azurerm_analysis_services_server` (S0 prod, D1 dev)
- `azurerm_analysis_services_server` firewall rules (Power BI service IPs)
- `azurerm_synapse_firewall_rule` (Power BI service IPs)

#### IaC ownership split
| Component | Owner |
|---|---|
| AAS server | `lakehouse-infra` Terraform |
| AAS tabular model (TMSL) | `lakehouse-app/aas/model.bim` via DevOps |
| Synapse Serverless external tables + views | `lakehouse-app/sql/` via DevOps |
| AAS pause/resume schedule | ADF pipeline in `lakehouse-app/adf/` |

---

### Phase 8 — Power BI

**DevOps pipeline:** `deploy-powerbi.yml` (Power BI REST API)

Power BI workspace management is not available in the `azurerm` Terraform provider. Workspaces,
datasets, and refresh schedules are managed via the Power BI REST API in a DevOps pipeline script.

#### Actions

1. Create Power BI workspaces via REST API in `deploy-powerbi.yml`.
2. Publish two dataset types:
   - **AAS Live Connection** — for standard dashboards. Queries AAS in-memory model.
     Sub-second response. Default for all consumers.
   - **Synapse Serverless DirectQuery** — for ad-hoc analyst workbooks where flexibility
     matters more than performance.
3. Assign Pro licenses to report authors ($10/user/month). Casual viewers access reports
   via published Power BI apps where possible to defer licensing cost.
4. Set refresh schedules to trigger after AAS refresh completes (post-Gold pipeline).

#### Licensing guidance
| Viewer count | Recommendation |
|---|---|
| < 25 viewers | Pro for authors only, viewers via published app |
| 25–100 viewers | Premium Per User ($20/user) for all active users |
| > 100 viewers | Evaluate Premium P1 ($4,995/month flat, unlimited viewers) |

---

### Phase 9 — Hardening & Handoff

#### Actions

1. **ADF Git discipline** — add branch protection to the ADF pipeline path in `lakehouse-app`.
   All pipeline changes via PR. The ADF Studio UI is treated as read-only in production.

2. **Spark pool cost cap** — set explicit `max_node_count` in the Synapse Spark pool Terraform
   resource. An uncapped autoscale on a misconfigured job can become expensive quickly.

3. **Azure Artifacts versioning policy** — enforce semantic versioning on `lakehouse-common`.
   Consumers pin to a minimum version in `requirements.txt`. Breaking changes require a major
   version bump.

4. **DR validation** — run a full recovery exercise before go-live:
   - Delete a Gold partition
   - Trigger Silver→Gold manually
   - Verify `replaceWhere` re-processing restores it cleanly
   - Repeat for a Bronze partition

5. **Late arrival SLA** — confirm `replaceWhere` windows on fact tables (7 days default) are
   wide enough for each source's known restatement patterns. Document source-specific windows
   in `_table_registry`.

6. **`_table_registry` handoff** — populate every Gold table entry with `owner_team`,
   `sla_by_utc`, and `description`. Domain teams sign off on their table definitions before
   the project is considered complete.

---

## IaC Ownership Reference

| Component | `lakehouse-infra` Terraform | `lakehouse-app` DevOps | Notes |
|---|---|---|---|
| Terraform state storage | Manual bootstrap | | One-time only |
| Resource group, VNET | ✅ | | |
| ADLS Gen2 (all 4 containers) | ✅ | | Includes quarantine |
| Key Vault + secrets | ✅ | | Values via tfvars / CI secrets |
| Managed identities + RBAC | ✅ | | Assigned before resources exist |
| ADF instance + Git config | ✅ | | Git points at lakehouse-app/adf/ |
| ADF pipelines, datasets, triggers | | ✅ ADF Git | JSON in lakehouse-app/adf/ |
| Azure Functions app | ✅ | | Consumption plan default |
| Function code + deployment | | ✅ deploy-functions.yml | |
| Common package (`lakehouse_common`) | | ✅ publish-common.yml | Published to Azure Artifacts |
| Synapse workspace + Spark pool | ✅ | | Auto-pause configured |
| Spark job scripts (PySpark) | | ✅ deploy-spark-jobs.yml | |
| Synapse Serverless external tables + views | | ✅ deploy-sql-scripts.yml | |
| AAS server | ✅ | | S0 prod / D1 dev |
| AAS tabular model (TMSL) | | ✅ deploy-aas-model.yml | |
| AAS pause/resume schedule | | ✅ ADF Git | Post-Gold trigger |
| Log Analytics workspace | ✅ | | First resource provisioned |
| Azure Monitor alerts | ✅ | | In monitoring/ module |
| Azure Monitor Workbook | ✅ | | workbook.json parameterised |
| Canary ADF pipelines | | ✅ ADF Git | In lakehouse-app/adf/ |
| pytest integration tests | | ✅ Scheduled pipeline | Every 15 min |
| Power BI workspaces + datasets | | ✅ deploy-powerbi.yml | Via REST API |
| `dq_results` Delta table | | Created by Spark job | First write creates table |
| `_table_registry` Delta table | | Created by Spark job | First write creates table |
| Local dev environment | Neither | | Docker Compose + Makefile |

---

## Example Project Budget Constraint

This repository is an example project. Azure spend must not exceed **$1 USD per month** across
all subscriptions used to demonstrate it. This constraint governs what gets provisioned versus
what exists only as Terraform/code definitions.

### What to deploy (fits within $1/month)

| Resource | Estimated cost | Notes |
|---|---|---|
| ADLS Gen2 storage account | ~$0.02 | Tiny sample dataset only — a few MB across bronze/silver/gold/quarantine containers |
| Azure Key Vault | ~$0.03 | Minimal secret operations |
| Log Analytics workspace | $0.00 | Stays within 5 GB/day free ingestion tier |
| Azure Functions (Consumption) | $0.00 | Stays within 1 M executions/month free grant |
| Synapse Serverless SQL pool | ~$0.01 | $5/TB scanned — negligible with sample data and partition pruning |
| **Total** | **< $0.10** | Comfortable margin below the $1 cap |

Azure DevOps (pipelines, repos, Artifacts) uses the free tier for open-source / ≤ 5 users and
does not count toward the Azure spend cap.

### What to define but NOT provision

The resources below are fully specified in Terraform and application code — the architecture,
configuration, and IaC are demonstrable — but they must remain commented out or gated behind a
`var.deploy_expensive_resources = false` flag so they are never applied against a real subscription.

| Resource | Reason for exclusion | Monthly cost if deployed |
|---|---|---|
| Azure Data Factory instance | Pipeline activity runs accrue charges immediately | ~$7–10 |
| Synapse Analytics workspace | Workspace fee applies even without Spark jobs | ~$1–2 |
| Synapse Spark pool | Minimum cluster charges apply even when auto-paused | ~$12–15 |
| Azure Analysis Services (any tier) | D1 (cheapest) is $57/month minimum | $57–336 |
| Azure DevOps self-hosted agent VM (B1s) | VM costs regardless of usage | ~$8 |
| Azure Monitor metric alerts | Per-alert charges | ~$1–3 |

### Enforcing the constraint in Terraform

Add the following variable to `lakehouse-infra/variables.tf` and gate all excluded resources
behind it:

```hcl
variable "deploy_expensive_resources" {
  description = "Set to true only in production. Must remain false for the example project."
  type        = bool
  default     = false

  validation {
    condition     = !var.deploy_expensive_resources
    error_message = "This is an example project. Azure spend must not exceed $1/month. Set deploy_expensive_resources = false."
  }
}
```

Use `count = var.deploy_expensive_resources ? 1 : 0` on every excluded resource block. This
ensures a `terraform plan` against the example environment will never schedule their creation.

### Local development as the primary demo path

Because most compute resources are excluded from Azure, the local Docker Compose environment
(see [Local Development Environment](#local-development-environment)) is the primary way to
demonstrate the full Bronze → Silver → Gold pipeline. All Spark jobs, validation rules,
ingestion clients, and SQL scripts run locally without any Azure credentials.

---

## Cost Estimates

> **Note:** The figures below are **production sizing targets**, included so the architecture
> can be costed before a real deployment decision is made. They do **not** apply to the example
> project, which is subject to the $1/month cap described above.

All figures are monthly USD at steady state (6 months of data accumulation, 50 APIs, ~2GB/day).
Three scenarios are modelled based on AAS usage hours and Power BI user count.

### Per-component costs

| Component | Lean | Standard | Full | Notes |
|---|---|---|---|---|
| **ADLS Gen2** | $8 | $8 | $8 | ~300GB bronze (cool after 90d), ~108GB silver+gold. Grows ~$1/mo |
| **Azure Data Factory** | $7 | $8 | $10 | 1,500 pipeline runs/mo. No DIU charges — Functions handles IO |
| **Azure Functions** | $0 | $0 | $1 | 1,500 executions/mo — within free grant of 1M |
| **Synapse Spark** | $12 | $12 | $15 | ~20 min/day session (B→S + S→G chained). 3 Small nodes, auto-pause |
| **Synapse Serverless SQL** | $1 | $2 | $3 | $5/TB scanned. Partition pruning keeps costs low |
| **Analysis Services (S0)** | $64 | $138 | $336 | Lean: paused ~140hr/mo. Standard: paused nights ~300hr/mo. Full: always-on |
| **Power BI Pro** | $50 | $150 | $300 | Lean: 5 users. Standard: 15 users. Full: 30 users. $10/user/mo |
| **Log Analytics + Monitor** | $3 | $3 | $4 | ~4.5GB/mo log ingestion — within 5GB free tier |
| **Azure DevOps** | $8 | $8 | $8 | Self-hosted B1s agent ($7.59/mo). Unlimited pipeline minutes |
| **Key Vault + misc** | $4 | $3 | $7 | Key Vault ops, Function storage account, Azure Artifacts (within free 2GB) |
| **Total** | **$157** | **$332** | **$692** | |

### Data pipeline cost (all scenarios)

The cost of moving and transforming data is approximately **$30/month** regardless of scenario.
AAS and Power BI licensing account for 73–91% of total cost.

| Component | Cost |
|---|---|
| ADLS Gen2 | $8 |
| ADF | $8 |
| Azure Functions | $0 |
| Synapse Spark | $12 |
| Synapse Serverless SQL | $2 |
| **Pipeline total** | **$30** |
