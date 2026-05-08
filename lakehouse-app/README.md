# lakehouse-app

Application code for the Azure Data Lakehouse — Spark jobs, Azure Functions, SQL, AAS model, and tests.

## Quick start (no Azure credentials needed)

```bash
cp .env.example .env
make install        # installs lakehouse-common in editable mode
make seed           # generates sample CSVs in data/local/bronze/
make bronze-silver  # runs Bronze→Silver locally (requires PySpark)
make silver-gold    # runs Silver→Gold locally
make test           # unit tests — no cluster needed
make lint           # ruff
```

To run with the full Docker environment:

```bash
make up             # starts PySpark + Jupyter at http://localhost:8888
make down           # stops containers
```

## Directory structure

| Directory | Purpose |
|---|---|
| `common/` | `lakehouse-common` shared Python package — published to Azure Artifacts |
| `ingestion/` | Azure Functions — API sources and FTP drops |
| `processing/` | PySpark jobs — Bronze→Silver and Silver→Gold |
| `validation/` | ValidationRule definitions per tier |
| `monitoring/` | Canary pings and heartbeat writer |
| `sql/` | Synapse Serverless DDL and Gold Delta CONSTRAINTS |
| `adf/` | ADF pipeline JSON (managed via ADF Git integration) |
| `aas/` | Analysis Services tabular model (TMSL) |
| `scripts/` | Local dev helpers — seed data, reset lakehouse |
| `tests/` | Unit tests (no cluster) and integration tests (live Azure) |
| `pipelines/` | Azure DevOps CI/CD pipeline definitions |

---

## Power BI access policy

### Dataset types

| Dataset | Mode | Audience |
|---|---|---|
| `lakehouse-aas-live` | AAS Live Connection | Dashboard authors and casual viewers |
| `lakehouse-serverless-dq` | Synapse Serverless DirectQuery | Analysts who need ad-hoc SQL access |

### Licensing

| Tier | Threshold | Cost driver |
|---|---|---|
| Power BI Pro | Up to ~25 active report authors | Per-user license (~$10/user/month) |
| Power BI Premium Per User (PPU) | ~25–500 users, or when paginated reports/AI features needed | Per-user (~$20/user/month) |
| Power BI Premium P1 | ~500+ viewers, or where embedding/large models required | Capacity-based (~$4,995/month) |

**Access model:** report authors hold Pro or PPU licenses. Casual viewers access via the published **Lakehouse Analytics** Power BI app, which requires no per-user license when the workspace is backed by Premium capacity. Below the P1 threshold, all consumers need at minimum a Pro license.

**Requesting access:** open a ticket in the data platform Jira project. The data engineering on-call will add the user to the appropriate Power BI workspace role (Viewer/Contributor/Member).

---

## Disaster recovery runbook

### Recovering a deleted Gold partition

Gold fact tables use `replaceWhere` over a 7-day window. Deleting a single date partition is recoverable by re-running the Silver→Gold job for that date.

```bash
# 1. Verify the partition is missing
az storage blob list \
  --account-name stlakehousedev \
  --container-name gold \
  --prefix "fact_orders/_date=2024-01-15/" \
  --auth-mode login

# 2. Re-trigger Silver→Gold in ADF for the affected date
az datafactory pipeline create-run \
  --factory-name adf-lakehouse-dev \
  --resource-group rg-lakehouse-dev \
  --name silver_to_gold \
  --parameters '{"processing_date": "2024-01-15"}'

# 3. Verify _table_registry shows updated last_refreshed_at
# (query silver/_table_registry via Synapse Serverless or locally)
```

**Observed recovery time (dev, single date partition):** ~8 minutes including AAS refresh.

### Recovering a deleted Bronze partition

If a Bronze NDJSON partition is lost, recovery requires re-ingestion from source.

```bash
# 1. Re-trigger the ADF source pipeline for the affected date
az datafactory pipeline create-run \
  --factory-name adf-lakehouse-dev \
  --resource-group rg-lakehouse-dev \
  --name ingest_sales \
  --parameters '{"date": "2024-01-15"}'

# 2. The pipeline automatically chains Bronze→Silver→Gold
# Monitor in ADF Studio or via:
az datafactory pipeline-run show \
  --factory-name adf-lakehouse-dev \
  --resource-group rg-lakehouse-dev \
  --run-id <run-id>
```

**Observed recovery time (dev, single source/date):** ~20 minutes end-to-end.

### Late-arrival data

The Silver→Gold job uses a 7-day `replaceWhere` window. Data arriving up to 7 calendar days late is automatically incorporated on the next scheduled run. For sources with known longer restatement windows, the window can be widened per-source in `processing/silver_to_gold/facts.py`.

| Source | Restatement window | Rationale |
|---|---|---|
| sales | 7 days | Order status updates within 5 business days |
| inventory | 2 days | Daily snapshot — rarely restated |
| partner_drops | 7 days | Partners may resend a weekly batch |

---

## On-call runbook

### Alert → workbook → KQL flow

1. **Alert fires** → Teams/Slack webhook via Azure Monitor action group `ag-lakehouse-<env>`.
2. **Open workbook** → Azure Portal → Monitor → Workbooks → "Lakehouse — `<env>` Operations".
3. **Pipeline Success Rate panel** → identify the failing pipeline and time window.
4. **DQ Violations panel** → filter by `table_name` to see which rule failed and how many rows.
5. **Tier Row Counts panel** → confirm `last_refreshed_at` is within SLA; check `freshness_status`.
6. **KQL deep-dive** — paste into Log Analytics:

```kql
// Recent ADF pipeline failures
ADFPipelineRun
| where TimeGenerated > ago(2h)
| where Status == "Failed"
| project TimeGenerated, PipelineName, RunId, ErrorMessage
| order by TimeGenerated desc

// DQ rule failures from Spark structured logs
AppTraces
| where TimeGenerated > ago(2h)
| where Properties.component == "dq-runner"
| where SeverityLevel >= 2
| extend rule = tostring(Properties.rule_name), failed = toint(Properties.failed_rows)
| project TimeGenerated, rule, failed, tostring(Properties.table_name)
```

### Escalation path

| Severity | Response time | Action |
|---|---|---|
| Pipeline failure (single retry exhausted) | 30 min | Page data-engineering on-call |
| DQ ERROR rate > 5% | 1 hour | Page data-engineering + notify domain team |
| Gold freshness > 26 h | 2 hours | Page data-engineering on-call |
| AAS unreachable | 15 min | Check pause/resume trigger; manually resume via portal |
