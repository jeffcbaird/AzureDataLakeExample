terraform {
  required_version = ">= 1.9.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }
}

provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy    = false
      recover_soft_deleted_key_vaults = true
    }
  }
  subscription_id = var.subscription_id
}

# ── Resource group ────────────────────────────────────────────────────────────

resource "azurerm_resource_group" "main" {
  name     = "rg-${var.project_name}-${var.environment}"
  location = var.location
  tags     = var.tags
}

# ── Cross-module derived values ───────────────────────────────────────────────
# Using locals + join() avoids python-hcl2 failures on template strings that
# contain index expressions like module.functions[0].foo.

locals {
  # HTTPS URL for the Function App — used as an ADF linked-service URL.
  functions_url = var.deploy_expensive_resources ? join("", ["https://", module.functions[0].function_app_hostname]) : null

  # Log Analytics workspace ID — passed to diagnostic settings on compute modules.
  workspace_id = var.deploy_expensive_resources ? module.monitoring[0].workspace_id : null

  # Function App resource ID — passed to monitoring for metric alert scoping.
  function_app_id = var.deploy_expensive_resources ? module.functions[0].function_app_id : null

  # Synapse serverless SQL endpoint — passed to monitoring for heartbeat alert.
  synapse_serverless_endpoint = var.deploy_expensive_resources ? module.synapse[0].synapse_serverless_sql_endpoint : null

  # Synapse workspace ARM resource ID — used by workbook to scope Serverless SQL queries.
  synapse_workspace_resource_id = var.deploy_expensive_resources ? module.synapse[0].synapse_workspace_id : ""
}

# ── Always-on modules (within $1/month budget) ────────────────────────────────

module "storage" {
  source = "./modules/storage"

  resource_group_name        = azurerm_resource_group.main.name
  location                   = azurerm_resource_group.main.location
  environment                = var.environment
  project_name               = var.project_name
  tags                       = var.tags
  log_analytics_workspace_id = local.workspace_id
}

module "key_vault" {
  source = "./modules/key_vault"

  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  environment         = var.environment
  project_name        = var.project_name
  tenant_id           = var.tenant_id
  tags                = var.tags
}

# ── Expensive modules — gated behind deploy_expensive_resources ───────────────
# Fully defined for reference; NOT provisioned in the example project.
# See Plan.md "Example Project Budget Constraint" for the exclusion rationale.

module "monitoring" {
  count  = var.deploy_expensive_resources ? 1 : 0
  source = "./modules/monitoring"

  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  environment         = var.environment
  project_name        = var.project_name
  tags                = var.tags

  alert_webhook_url             = var.alert_webhook_url
  source_names                  = var.source_names
  function_app_id               = local.function_app_id
  synapse_serverless_endpoint   = local.synapse_serverless_endpoint
  synapse_workspace_resource_id = local.synapse_workspace_resource_id
}

module "functions" {
  count  = var.deploy_expensive_resources ? 1 : 0
  source = "./modules/functions"

  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  environment         = var.environment
  project_name        = var.project_name
  key_vault_id        = module.key_vault.key_vault_id
  storage_account_id  = module.storage.storage_account_id
  tags                = var.tags

  key_vault_uri              = module.key_vault.key_vault_uri
  log_analytics_workspace_id = local.workspace_id
}

module "data_factory" {
  count  = var.deploy_expensive_resources ? 1 : 0
  source = "./modules/data_factory"

  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  environment         = var.environment
  project_name        = var.project_name
  key_vault_id        = module.key_vault.key_vault_id
  storage_account_id  = module.storage.storage_account_id
  tags                = var.tags

  tenant_id                  = var.tenant_id
  devops_account_name        = var.devops_account_name
  devops_project_name        = var.devops_project_name
  function_app_url           = local.functions_url
  log_analytics_workspace_id = local.workspace_id
}

module "synapse" {
  count  = var.deploy_expensive_resources ? 1 : 0
  source = "./modules/synapse"

  resource_group_name                  = azurerm_resource_group.main.name
  location                             = azurerm_resource_group.main.location
  environment                          = var.environment
  project_name                         = var.project_name
  key_vault_id                         = module.key_vault.key_vault_id
  adls_primary_dfs_endpoint            = module.storage.adls_primary_dfs_endpoint
  storage_data_lake_gen2_filesystem_id = module.storage.gold_filesystem_id
  log_analytics_workspace_id           = local.workspace_id
  tags                                 = var.tags
}

module "analysis_services" {
  count  = var.deploy_expensive_resources ? 1 : 0
  source = "./modules/analysis_services"

  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  environment         = var.environment
  project_name        = var.project_name
  sku                 = var.environment == "prod" ? "S0" : "D1"
  admin_users         = var.aas_admin_users
  tags                = var.tags
}
