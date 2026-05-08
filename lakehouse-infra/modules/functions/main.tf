# Azure Functions — Consumption (Y1) plan with system-assigned managed identity.
# To escape the Consumption plan, change sku_name to "EP1" and remove the Y1 comment.

locals {
  func_name    = "func-${var.project_name}-${var.environment}"
  plan_name    = "plan-${var.project_name}-${var.environment}"
  # Derive the storage account name from its resource ID (index 8 in the ARM path).
  storage_name = element(split("/", var.storage_account_id), 8)
}

# ── Consumption plan (Y1 = effectively free at low invocation rates) ──────────

resource "azurerm_service_plan" "main" {
  name                = local.plan_name
  location            = var.location
  resource_group_name = var.resource_group_name
  os_type             = "Linux"
  sku_name            = "Y1"
  tags                = var.tags
}

# ── Function App ───────────────────────────────────────────────────────────────

resource "azurerm_linux_function_app" "main" {
  name                = local.func_name
  location            = var.location
  resource_group_name = var.resource_group_name
  service_plan_id     = azurerm_service_plan.main.id
  tags                = var.tags

  # Use the ADLS storage account for function state; MI auth replaces conn string.
  # NOTE: the function app MI must hold Storage Blob Data Owner + Storage Queue
  # Data Contributor + Storage Table Data Contributor on this account — granted
  # via rbac.tf when deploy_expensive_resources = true.
  storage_account_name          = local.storage_name
  storage_uses_managed_identity = true

  identity {
    type = "SystemAssigned"
  }

  site_config {
    application_stack {
      python_version = "3.11"
    }
  }

  app_settings = merge(
    {
      # Key Vault URI for reference-style secrets in app settings
      "KEYVAULT_URI" = var.key_vault_uri

      # App Insights connection string pulled from KV at runtime
      "APPLICATIONINSIGHTS_CONNECTION_STRING" = "@Microsoft.KeyVault(SecretUri=${var.key_vault_uri}secrets/appinsights-connection-string/)"

      # Deploy from a zip package
      "WEBSITE_RUN_FROM_PACKAGE" = "1"
    },
    # Private PyPI feed — only set when an Artifacts feed URL is provided
    var.artifacts_feed_url != "" ? {
      "PIP_EXTRA_INDEX_URL" = var.artifacts_feed_url
    } : {}
  )
}

# ── Diagnostic setting → Log Analytics ────────────────────────────────────────

resource "azurerm_monitor_diagnostic_setting" "functions" {
  count                      = var.log_analytics_workspace_id != null ? 1 : 0
  name                       = "diag-func-${var.environment}"
  target_resource_id         = azurerm_linux_function_app.main.id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  enabled_log { category = "FunctionAppLogs" }
  metric { category = "AllMetrics" }
}
