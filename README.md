# AzureDataLakeExample

An example Azure data lakehouse project demonstrating a full Bronze → Silver → Gold pipeline architecture using Azure Data Lake Storage Gen2, Synapse Analytics, Azure Data Factory, Azure Functions, and Power BI. The entire infrastructure is defined as code using Terraform.

> **Example project — $1/month Azure spend cap.** Most compute resources are fully defined but not provisioned. See `Plan.md` for the budget constraint details.

---

## Repository structure

```
AzureDataLakeExample/
├── Plan.md                        # Architecture and implementation plan (start here)
├── Tasks.md                       # Sequenced task list that operationalises Plan.md
├── README.md                      # This file
│
├── lakehouse-infra/               # Terraform infrastructure — all Azure resources
│   ├── backend.tf                 # Remote state configuration → Azure Storage Account
│   ├── main.tf                    # Root module — wires all sub-modules together
│   ├── variables.tf               # Input variables incl. the $1/month spend-cap guard
│   ├── outputs.tf                 # Root-level outputs (resource group, storage, KV)
│   ├── terraform.tfvars.example   # Copy to terraform.tfvars and fill in real values
│   ├── .terraform.lock.hcl        # Provider version lock file (managed by terraform init)
│   ├── .gitignore                 # Excludes .terraform/, *.tfstate, terraform.tfvars
│   │
│   ├── environments/
│   │   ├── dev.tfvars             # Variable values for the dev environment
│   │   └── prod.tfvars            # Variable values for prod (expensive resources off by default)
│   │
│   ├── modules/
│   │   ├── storage/               # ADLS Gen2 — 4 containers, lifecycle rules, diagnostics (Phase 1)
│   │   ├── key_vault/             # Key Vault with RBAC, soft-delete, secret management (Phase 2)
│   │   ├── data_factory/          # ADF instance, Git integration, linked services (Phase 3 stub)
│   │   ├── functions/             # Azure Functions app on Consumption plan (Phase 3 stub)
│   │   ├── synapse/               # Synapse workspace + Spark pool + Serverless SQL (Phase 5 stub)
│   │   ├── analysis_services/     # Azure Analysis Services S0/D1 (Phase 7 stub)
│   │   └── monitoring/            # Log Analytics, Monitor alerts, Workbook (Phase 4 stub)
│   │       └── workbook.json      # Azure Monitor Workbook definition (parameterised)
│   │
│   └── pipelines/
│       ├── tf-plan.yml            # Azure DevOps pipeline — runs on PR: fmt + validate + plan
│       └── tf-apply.yml           # Azure DevOps pipeline — runs on merge to main: apply (dev → prod)
│
└── lakehouse-app/                 # Application code — Spark jobs, Functions, SQL, tests
    └── pipelines/
        └── run-integration-tests.yml  # Scheduled every 15 min — pings source APIs and FTP hosts
```

The `lakehouse-app/` directory will be fully scaffolded in Phase 0.4. See `Tasks.md` for the current progress.

---

## Modules at a glance

| Module | Always deployed | Cost | Phase |
|---|---|---|---|
| `storage` | ✅ Yes | ~$0.02/mo | 1 |
| `key_vault` | ✅ Yes | ~$0.03/mo | 2 |
| `monitoring` | ❌ Gated | ~$3–4/mo | 4 |
| `data_factory` | ❌ Gated | ~$7–10/mo | 3 |
| `functions` | ❌ Gated | ~$0–1/mo | 3 |
| `synapse` | ❌ Gated | ~$12–15/mo | 5 |
| `analysis_services` | ❌ Gated | ~$57–336/mo | 7 |

Gated modules are controlled by the `deploy_expensive_resources` variable in `variables.tf`. It defaults to `false` and a validation block prevents it from being set to `true` without an explicit code change — ensuring nothing is accidentally provisioned against the example project.

---

## Getting started

### Prerequisites

- [Terraform](https://developer.hashicorp.com/terraform/install) >= 1.9
- [Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli) — run `az login --tenant <tenant-id>` before any Terraform commands
- Azure subscription with the Terraform state storage account already created (see `Plan.md § Phase 0.2`)
- All environments default to **West US 2** (`westus2`). Override via the `location` variable in your tfvars if needed.

### First run

```bash
cd lakehouse-infra

# Copy and fill in your subscription/tenant IDs
cp terraform.tfvars.example terraform.tfvars

# Initialise — downloads the azurerm provider and connects to remote state
terraform init

# Preview what will be created (storage account + Key Vault only)
terraform plan -var-file=environments/dev.tfvars

# Apply
terraform apply -var-file=environments/dev.tfvars
```

### Running with a different environment

```bash
```

---

## Key documents

| File | Purpose |
|---|---|
| `Plan.md` | Full architecture, cost estimates, phase-by-phase implementation guide |
| `Tasks.md` | Granular task checklist — check items off as they land |
| `lakehouse-infra/variables.tf` | All configurable inputs; the spend-c