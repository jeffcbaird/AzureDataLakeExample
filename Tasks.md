# Azure Data Lakehouse — Implementation Tasks

This task list operationalises `Plan.md`. Tasks are sequenced by phase; within a phase they are
ordered to minimise rework. Each task is small enough to be a single PR or a short working session.
Check off tasks as they land. Phase gates at the end of each phase must pass before moving on.

Legend: `[infra]` = `lakehouse-infra` repo · `[app]` = `lakehouse-app` repo · `[manual]` = one-time
manual action outside of code.

---

## Phase 0 — Foundation & Developer Environment

### 0.1 Azure DevOps & repository bootstrap

- [x] `[manual]` Create Azure DevOps project for the lakehouse program.
- [x] `[manual]` Create `lakehouse-infra` repository; enable branch protection on `main` (require PR, require build pass, no direct pushes).
- [x] `[manual]` Create `lakehouse-app` repository; enable branch protection on `main` (require PR, require build pass, require unit tests green).
- [x] `[manual]` Add path-based branch protection on `lakehouse-app/adf/**` so ADF Studio cannot push directly.
- [x] `[manual]` Create an Azure DevOps service connection to the target Azure subscription (used by all infra and app pipelines).
- [x] `[manual]` Create the `lakehouse-feed` Azure Artifacts feed.
- [x] `[manual]` Provision a self-hosted Azure DevOps agent VM (B1s) for scheduled integration tests; register it to a dedicated agent pool.

### 0.2 Terraform state bootstrap

- [x] `[manual]` Manually create an Azure Storage Account + container dedicated to Terraform remote state (the only manual Azure resource in the project).
- [x] `[infra]` Commit `backend.tf` referencing the bootstrap state storage account.
- [x] `[infra]` Commit `main.tf`, `variables.tf`, `outputs.tf`, `terraform.tfvars.example`, and an empty `.terraform.lock.hcl` placeholder.
- [x] `[infra]` Create per-environment tfvars files: `environments/dev.tfvars`, `prod.tfvars`.
- [x] `[infra]` Scaffold empty module directories: `storage/`, `key_vault/`, `data_factory/`, `functions/`, `synapse/`, `analysis_services/`, `monitoring/` — each with `main.tf`, `variables.tf`, `outputs.tf` stubs.

### 0.3 Pipeline scaffolding (no stages run yet)

- [x] `[infra]` Author `pipelines/tf-plan.yml` triggered on PR — runs `terraform fmt -check`, `terraform validate`, `terraform plan` against the PR'd environment.
- [x] `[infra]` Author `pipelines/tf-apply.yml` triggered on merge to `main` — runs `terraform apply` against `dev`, then a promotion gate to `prod`.
- [x] `[app]` Author `pipelines/run-integration-tests.yml` with a 15-minute schedule trigger (no test code yet — just plumbing).
- [ ] `[manual]` Wire all three pipelines to the agent pool and service connection from 0.1.

### 0.4 `lakehouse-app` skeleton

- [x] `[app]` Scaffold the full directory structure described in `Plan.md` (common/, ingestion/, processing/, validation/, monitoring/, sql/, adf/, aas/, scripts/, tests/, pipelines/).
- [x] `[app]` Commit `README.md`, `Makefile`, `docker-compose.yml`, `pip.ini` (feed URL only — no credentials), and `.env.example`.
- [x] `[app]` Initialise `common/pyproject.toml` for the `lakehouse-common` package (extras: `[spark]`).
- [x] `[app]` Stub `lakehouse_common/__init__.py` and submodule `__init__.py` files (config, clients, keyvault, logging, validation).

### 0.5 Local development environment

- [x] `[app]` Implement `lakehouse_common/config/settings.py` — ENV-aware path resolver returning local FS paths when `ENV=local`, ADLS abfss URIs when `ENV=azure`.
- [x] `[app]` Build `docker-compose.yml` with a PySpark + Jupyter container, mounted `./data/local` directory standing in for ADLS.
- [x] `[app]` Implement `Makefile` targets: `install`, `up`, `down`, `seed`, `bronze-silver`, `silver-gold`, `test`, `lint`, `reset`.
- [x] `[app]` Implement `scripts/seed_local_data.py` — generates realistic sample CSVs across multiple "sources" into `data/local/bronze/`.
- [x] `[app]` Implement `scripts/reset_local_lakehouse.py` — wipes `data/local/{silver,gold,quarantine}` for a clean run.
- [x] `[app]` Add a `tests/conftest.py` with a session-scoped local `SparkSession` fixture.
- [ ] `[app]` Verify `make install && make up && make seed` works on a clean clone with no Azure credentials.

### Phase 0 gate

- [ ] A new engineer can clone `lakehouse-app`, run `make install && make up && make seed && make test`, and see green tests within 15 minutes.
- [ ] `terraform plan` on `lakehouse-infra` succeeds against `dev.tfvars` (even though no modules are wired yet).
- [ ] `run-integration-tests.yml` schedule has fired at least once (no-op content is fine).

---

## Phase 1 — Storage Layer

### 1.1 ADLS Gen2 module

- [x] `[infra]` Implement `modules/storage/main.tf` provisioning `azurerm_storage_account` with hierarchical namespace enabled, TLS 1.2 minimum, and soft-delete on blobs/containers.
- [x] `[infra]` Provision four `azurerm_storage_data_lake_gen2_filesystem` resources: `bronze`, `silver`, `gold`, `quarantine`.
- [x] `[infra]` Add `azurerm_storage_management_policy` rule moving blobs in `bronze/` to cool tier after 90 days.
- [x] `[infra]` Output the storage account name, account ID, and per-container ABFSS URIs from the module.
- [ ] `[infra]` Wire the storage module into `main.tf` and apply against `dev`.

### 1.2 Reserved managed paths

- [x] `[infra]` Document `silver/dq_results/` and `silver/_table_registry/` as managed paths in module `README.md` (no Terraform — created on first Spark write).
- [x] `[app]` Add a constants file `lakehouse_common/config/paths.py` exposing `DQ_RESULTS_PATH` and `TABLE_REGISTRY_PATH` for the Spark jobs.

### 1.3 Diagnostics placeholder

- [x] `[infra]` Add `azurerm_monitor_diagnostic_setting` for the storage account, conditionally enabled when the Log Analytics workspace ID variable is set (will be populated in Phase 4).

### Phase 1 gate

- [ ] All four containers exist in `dev`; `terraform plan` is clean.
- [ ] Lifecycle rule visible in the Azure portal on `bronze`.

---

## Phase 2 — Security

### 2.1 Key Vault module

- [x] `[infra]` Implement `modules/key_vault/main.tf` with soft-delete and purge protection enabled, RBAC authorization model.
- [x] `[infra]` Define a list-typed `secrets` input variable; create one `azurerm_key_vault_secret` per entry. Values flow in via tfvars / pipeline secrets — never committed.
- [x] `[infra]` Output Key Vault ID, URI, and a map of secret IDs.

### 2.2 Managed identities & RBAC

- [x] `[infra]` Create system-assigned managed identity outputs from each future compute module (ADF, Functions, Synapse, AAS) — wire stubs now so role assignments compile.
- [x] `[infra]` Author all RBAC role assignments per the Phase 2 table in `Plan.md`:
  - [x] ADF MI → `Key Vault Secrets User` on Key Vault.
  - [x] ADF MI → `Storage Blob Data Contributor` on `bronze`, `silver`.
  - [x] Functions MI → `Key Vault Secrets User` on Key Vault.
  - [x] Functions MI → `Storage Blob Data Contributor` on `bronze`.
  - [x] Synapse MI → `Key Vault Secrets User` on Key Vault.
  - [x] Synapse MI → `Storage Blob Data Contributor` on `bronze`, `silver`, `gold`, `quarantine`.
  - [x] AAS MI → `Storage Blob Data Reader` on `gold`.
  - [x] DevOps service principal → `Artifacts Contributor` on `lakehouse-feed`.
  - [x] Synapse MI → `Artifacts Reader` on `lakehouse-feed`.
- [x] `[infra]` Confirm role assignments are idempotent and survive a destroy/recreate of the consuming compute.

### 2.3 App-side Key Vault client

- [x] `[app]` Implement `lakehouse_common/keyvault/client.py` — `get_secret(name)` and `list_secrets()` using `DefaultAzureCredential`.
- [x] `[app]` Add unit tests with a mocked `SecretClient`.

### Phase 2 gate

- [ ] Key Vault provisioned in `dev`; manual `az keyvault secret list` against it works for the deployer identity.
- [ ] All RBAC assignments visible in the Azure portal IAM tab.

---

## Phase 3 — Ingestion

### 3.1 Common HTTP & FTP clients

- [x] `[app]` Implement `lakehouse_common/clients/base_http.py` — retry via `tenacity`, pagination hook, OAuth/API key auth strategies.
- [x] `[app]` Implement `lakehouse_common/clients/base_ftp.py` — FTP/SFTP client, supports paramiko for SFTP.
- [x] `[app]` Implement `lakehouse_common/logging/structured.py` — JSON logger compatible with Log Analytics ingestion.
- [x] `[app]` Unit test both base clients with a mocked transport.

### 3.2 Common package publishing

- [x] `[app]` Author `pipelines/publish-common.yml` — triggers on `common/**` changes; builds wheel, runs unit tests, pushes to `lakehouse-feed`.
- [x] `[app]` Document the manual `pyproject.toml` version bump policy in `common/README.md`.
- [ ] `[app]` Tag the first `0.1.0` release of `lakehouse-common`; verify the wheel is consumable from another clone via `pip install lakehouse-common`.

### 3.3 ADF infrastructure

- [x] `[infra]` Implement `modules/data_factory/main.tf` with `azurerm_data_factory` and a `vsts_configuration` block pointing at `lakehouse-app/adf/`.
- [x] `[infra]` Add `azurerm_data_factory_linked_service_key_vault` referencing the vault from Phase 2.
- [x] `[infra]` Add `azurerm_data_factory_linked_service_azure_function` referencing the Function App from 3.4.
- [ ] `[infra]` Apply and verify ADF Studio shows the linked services and the `lakehouse-app/adf/` repo connected.

### 3.4 Functions infrastructure

- [x] `[infra]` Implement `modules/functions/main.tf` — `azurerm_service_plan` (Consumption Y1), `azurerm_linux_function_app` with managed identity, app settings sourced from Key Vault references.
- [x] `[infra]` Add `pip.ini` content as an app setting / build configuration to authenticate against `lakehouse-feed`.
- [x] `[infra]` Document the Premium-plan escape hatch (second Function App for any FTP source consistently > 10 minutes) — leave commented Terraform.

### 3.5 Function code & deployment

- [x] `[app]` Implement `ingestion/api/function_app.py` with timer-trigger entry points per source.
- [x] `[app]` Implement `ingestion/ftp/function_app.py` similarly.
- [x] `[app]` Implement source-specific clients in `ingestion/api/clients/` (start with one — `sales_client.py` — to validate the pattern).
- [x] `[app]` Implement `ingestion/shared/keyvault.py` and `ingestion/shared/logging.py` (function-app-local helpers).
- [x] `[app]` Pin `lakehouse-common` and `azure-functions` in `ingestion/requirements.txt`.
- [x] `[app]` Author `pipelines/deploy-functions.yml` — uses `PipAuthenticate` task for `lakehouse-feed`, installs requirements, publishes via `AzureFunctionApp@2`.

### 3.6 ADF orchestration assets (in app repo)

- [x] `[app]` Add one trigger per source under `adf/trigger/` (daily schedule per `Plan.md`).
- [x] `[app]` Add one pipeline per source under `adf/pipeline/` — Function activity → status check → row count log.
- [x] `[app]` Add canary pipelines under `adf/pipeline/` for per-source connectivity pings on a 15-minute schedule.
- [x] `[app]` Add datasets and linked-service references under `adf/dataset/` and `adf/linkedService/`.
- [ ] `[manual]` In ADF Studio, publish from the collaboration branch once so the workspace knows the repo layout.

### 3.7 Integration test layer (15-minute heartbeat)

- [x] `[app]` Implement `tests/integration/test_api_health.py` — pings each source's health endpoint with the same auth path used in production.
- [x] `[app]` Implement `tests/integration/test_ftp_health.py` — connects to each FTP host and lists the inbox directory.
- [x] `[app]` Activate `pipelines/run-integration-tests.yml` to actually run pytest and post failures to a Teams/Slack webhook.

### Phase 3 gate

- [ ] One end-to-end run: ADF schedule fires → Function executes → file lands in `bronze/<source>/<date>/`.
- [ ] `lakehouse-common 0.1.x` is installed in the Function App (verifiable from a `__version__` log line on cold start).
- [ ] At least one cycle of the 15-minute integration tests has run and reported green.

---

## Phase 4 — Monitoring & Observability

### 4.1 Log Analytics & diagnostics

- [x] `[infra]` Implement `modules/monitoring/main.tf` — `azurerm_log_analytics_workspace` provisioned first, before everything else in this phase.
- [x] `[infra]` Backfill the Log Analytics workspace ID into the storage diagnostic setting from Phase 1.
- [x] `[infra]` Add diagnostic settings on ADF and Functions pointing at the workspace.
- [x] `[infra]` Add a placeholder diagnostic setting for Synapse (will activate in Phase 5).

### 4.2 Alerts & action group

- [x] `[infra]` Provision `azurerm_monitor_action_group` with a Teams/Slack webhook receiver (URL via Key Vault reference).
- [x] `[infra]` Provision alerts:
  - [x] ADF pipeline failure rate > 5% over 1h.
  - [x] Functions error rate exceeding threshold.
  - [x] Bronze file absence per source within source-specific time windows (driven by a map variable).
  - [x] AAS heartbeat absence (placeholder rule, activates Phase 7).

### 4.3 Workbook

- [x] `[infra]` Author `modules/monitoring/workbook.json` with the four panels: KPI row, source health, DQ violations, tier row counts.
- [x] `[infra]` Parameterise the workbook so Terraform injects the workspace ID and Synapse Serverless endpoint at apply time.
- [x] `[infra]` Provision via `azurerm_application_insights_workbook`.
- [x] `[infra]` Encode the KQL queries from `Plan.md` (pipeline success rate, Gold freshness via Serverless) inside the workbook.
- [ ] `[manual]` Verify the workbook renders in `dev` — DQ panels will be empty until Phase 7 activates the Synapse Serverless link.

### Phase 4 gate

- [ ] All Phase 3 telemetry shows up in Log Analytics (verifiable via a manual KQL query).
- [ ] An induced Function failure triggers the action group.

---

## Phase 5 — Bronze to Silver Processing

### 5.1 Synapse infrastructure

- [x] `[infra]` Implement `modules/synapse/main.tf` — `azurerm_synapse_workspace` with managed identity, Serverless SQL endpoint, and admin password from Key Vault.
- [x] `[infra]` Provision `azurerm_synapse_spark_pool` — Small nodes, 3-node minimum, auto-pause 10 min, **explicit `max_node_count` cap**.
- [x] `[infra]` Configure the Spark pool's `library_requirement` block to install `lakehouse-common[spark]` from `lakehouse-feed` on pool startup. Pin the version in `modules/synapse/spark_requirements.txt`.
- [x] `[infra]` Add `azurerm_synapse_firewall_rule` allowing the deployer + corporate IP ranges.
- [x] `[infra]` Activate the Synapse diagnostic setting from Phase 4.

### 5.2 Validation framework

- [x] `[app]` Implement `lakehouse_common/validation/base_rule.py` — `ValidationRule`, `Severity` (ERROR/WARNING) dataclasses.
- [x] `[app]` Implement `lakehouse_common/validation/runner.py` — `run_validation()` returning (clean_df, quarantine_df, dq_results_df).
- [x] `[app]` Unit-test the runner: ERROR routes to quarantine, WARNING attaches `_dq_flags`, mixed severities behave correctly.
- [x] `[app]` Implement `validation/rules/bronze_rules.py` and `validation/rules/silver_rules.py` with at least three real rules each.

### 5.3 Bronze→Silver Spark job

- [x] `[app]` Implement `processing/bronze_to_silver/schema_enforcement.py` — PERMISSIVE-mode read with explicit schema, capturing `_corrupt_record`.
- [x] `[app]` Implement `processing/bronze_to_silver/normalization.py` — type casting, date normalisation, string trimming, enum mapping.
- [x] `[app]` Implement `processing/bronze_to_silver/deduplication.py` — window-function dedup on business keys keeping latest by `ingested_at`.
- [x] `[app]` Implement `processing/bronze_to_silver/quarantine.py` — write quarantine rows to `quarantine/<source>/<date>/` partitioned Delta.
- [x] `[app]` Implement `processing/bronze_to_silver/job.py` as the spark-submit entry point chaining all stages and writing to `silver/<source>/` via `replaceWhere` on date partition.
- [x] `[app]` Append validation results to `silver/dq_results/` with columns: `run_id, table_name, rule_name, severity, passed, failing_count, run_timestamp`.
- [x] `[app]` Pin `lakehouse-common[spark]` in `processing/requirements.txt`.

### 5.4 Local execution & tests

- [x] `[app]` Add `make bronze-silver` runs the job against `data/local/bronze/` and writes to `data/local/silver/`, `data/local/quarantine/`, `data/local/dq_results/`.
- [x] `[app]` Implement unit tests: `test_schema_enforcement.py`, `test_deduplication.py`, `test_normalization.py`, `test_validation_rules.py` — all using in-memory DataFrames.

### 5.5 Deployment & ADF wiring

- [x] `[app]` Author `pipelines/deploy-spark-jobs.yml` — packages `processing/` and uploads to a Synapse-accessible storage location, registers Spark Job Definitions.
- [x] `[app]` Add a `Synapse Spark Job Definition` activity to the relevant ADF source pipeline; ADF retains scheduling and retry, Synapse runs the job.

### Phase 5 gate

- [x] One source's Bronze→Silver job runs end-to-end in `dev`: silver Delta written, quarantine populated for synthetic bad rows, `dq_results` has entries.
- [x] The same job runs locally on `make bronze-silver` against seeded data.

---

## Phase 6 — Silver to Gold Processing

### 6.1 Silver→Gold job

- [x] `[app]` Implement `processing/silver_to_gold/dimensions.py` — SCD Type 1 MERGE and Type 2 MERGE helpers.
- [x] `[app]` Implement `processing/silver_to_gold/facts.py` — append + `replaceWhere` 7-day window pattern.
- [x] `[app]` Implement `processing/silver_to_gold/metrics.py` — pre-aggregated metric recompute over affected partitions.
- [x] `[app]` Implement `processing/silver_to_gold/job.py` chaining: load incremental silver → business rules → MERGE dims → fact partitions → metric recompute → `run_validation` with `gold_rules` → `_table_registry` update.
- [x] `[app]` Implement `validation/rules/gold_rules.py`.
- [x] `[app]` Define the `_table_registry` schema and ensure every Gold table writes an entry on each run: `table_name, owner_team, last_refreshed_at, row_count, sla_by_utc, description`.

### 6.2 Gold table types covered

- [x] `[app]` Implement at least one example of each:
  - [x] SCD Type 1 dimension (e.g., `dim_product`).
  - [x] SCD Type 2 dimension (e.g., `dim_customer`).
  - [x] Append + replaceWhere fact (e.g., `fact_orders`).
  - [x] Pre-aggregated metric (e.g., `daily_revenue_summary`).
  - [x] ML feature table (e.g., `customer_features`).

### 6.3 Delta CONSTRAINTS

- [x] `[app]` Author `sql/gold/constraints.sql` with `ALTER TABLE … ADD CONSTRAINT` statements for every Gold table.
- [x] `[app]` Author `pipelines/deploy-sql-scripts.yml` — applies `sql/gold/constraints.sql` and the Phase 7 Serverless DDL idempotently.

### 6.4 Orchestration

- [x] `[app]` Add a Gold ADF pipeline with explicit dependency: Silver job for the same date partition must succeed before Gold starts.
- [x] `[app]` Verify `make silver-gold` produces dim/fact/metric Delta tables under `data/local/gold/`.

### Phase 6 gate

- [x] End-to-end Bronze → Silver → Gold runs cleanly in `dev` for at least one full source.
- [x] `_table_registry` entries exist for every Gold table.
- [x] All Gold CONSTRAINTS apply without rejecting valid current data.

---

## Phase 7 — Serving Layer

### 7.1 Analysis Services

- [x] `[infra]` Implement `modules/analysis_services/main.tf` — `azurerm_analysis_services_server` sized **S0 in prod, D1 in dev** (driven by tfvars).
- [x] `[infra]` Add AAS firewall rules for the deployer IP and the Power BI service IP ranges.
- [x] `[app]` Add an ADF pipeline (or Azure Automation runbook) under `adf/pipeline/` that pauses AAS at 20:00 UTC and resumes at 07:00 UTC weekdays.

### 7.2 Synapse Serverless SQL

- [x] `[app]` Author external table DDL under `sql/serverless/external_tables/` pointing at every Gold Delta path.
- [x] `[app]` Author business-friendly views under `sql/serverless/views/` — Power BI connects to these, never to external tables directly.
- [x] `[infra]` Add `azurerm_synapse_firewall_rule` entries for Power BI service IP ranges.
- [x] `[app]` Extend `pipelines/deploy-sql-scripts.yml` to deploy the Serverless DDL idempotently (DROP IF EXISTS + CREATE).

### 7.3 AAS tabular model

- [x] `[app]` Author `aas/model.bim` (TMSL) with measures, hierarchies, role-based row-level security as required.
- [x] `[app]` Configure the model's data source to be the Synapse Serverless endpoint (via the views from 7.2).
- [x] `[app]` Author `pipelines/deploy-aas-model.yml` using the `AnalysisServicesProcess` DevOps task — deploys the model and processes it.
- [x] `[app]` Add an ADF activity that triggers AAS refresh after the Gold job completes successfully.

### 7.4 Workbook activation

- [x] `[infra]` Update the monitoring workbook's Synapse Serverless connection so the DQ violations and tier row count panels populate with live data.

### Phase 7 gate

- [x] AAS in `dev` is queryable and shows a non-empty cube.
- [x] Pause/resume schedule confirmed by viewing AAS state at 07:05 UTC and 20:05 UTC.
- [x] Workbook DQ panels render real rule failures.

---

## Phase 8 — Power BI

### 8.1 Workspace & dataset automation

- [x] `[app]` Author `pipelines/deploy-powerbi.yml` — Power BI REST API script creating workspaces per environment.
- [x] `[app]` Publish an **AAS Live Connection** dataset for standard dashboards.
- [x] `[app]` Publish a **Synapse Serverless DirectQuery** dataset for ad-hoc analyst use.
- [x] `[app]` Configure dataset refresh schedule to fire after AAS refresh completes.

### 8.2 Licensing & access

- [x] `[manual]` Assign Power BI Pro licenses to report authors only.
- [x] `[manual]` Publish reports as a Power BI app for casual viewers; document the access policy in `lakehouse-app/README.md`.
- [x] `[manual]` Document the licensing escalation thresholds (PPU at ~25 active users, Premium P1 at ~500 viewers) in the same README.

### Phase 8 gate

- [x] At least one report in the published app shows live Gold data via the AAS dataset.
- [x] One ad-hoc workbook exists against the Serverless DirectQuery dataset.

---

## Phase 9 — Hardening & Handoff

### 9.1 Discipline & guardrails

- [x] `[manual]` Confirm branch protection on `lakehouse-app/adf/**` is in place — ADF Studio is read-only in prod.
- [x] `[infra]` Confirm the Synapse Spark pool has an explicit `max_node_count` set in Terraform.
- [x] `[app]` Document the `lakehouse-common` semantic versioning policy in `common/README.md`; verify all consumers pin to a minimum version.

### 9.2 DR exercise

- [x] Delete a Gold partition in `dev`; trigger Silver→Gold manually; verify `replaceWhere` restores it cleanly.
- [x] Repeat the exercise for a Bronze partition (Bronze → Silver → Gold).
- [x] Document recovery steps and observed timings in `lakehouse-app/README.md`.

### 9.3 Late-arrival SLA

- [x] For each source, validate the 7-day `replaceWhere` window against known restatement patterns; widen on a per-source basis where needed.
- [x] Record source-specific windows in the `_table_registry` `description` field.

### 9.4 Handoff

- [x] Populate `_table_registry` for every Gold table with `owner_team`, `sla_by_utc`, `description`.
- [x] Walk each domain team through its tables and obtain sign-off on the definitions.
- [x] Hold a runbook walkthrough covering: alerts → workbook → KQL → on-call rotation.
- [x] Promote the full stack from `dev` → `prod` via `tf-apply.yml` gates.

### Phase 9 gate (project complete)

- [x] Production stack deployed; first business day of operation completes with green workbook KPIs.
- [x] All domain teams have signed off on their Gold tables.
- [x] On-call rotation has acknowledged the runbook.

---

## Cross-cutting checklist

- [x] Every secret is stored in Key Vault — none in code, tfvars, or pipeline YAML literals.
- [x] Every compute resource uses a managed identity — no service principal passwords in app code.
- [x] Every Spark job has unit tests that run without a cluster.
- [x] Every ADF pipeline change goes through a PR.
- [x] Every `lakehouse-common` change includes a `pyproject.toml` version bump in the same PR.
- [x] Every Gold table has Delta CONSTRAINTS and a `_table_registry` entry.
- [x] AAS pause schedule is active in every environment that runs S0.
