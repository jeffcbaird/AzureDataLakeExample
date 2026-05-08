# Azure Data Factory — managed identity + Git integration + linked services.

resource "azurerm_data_factory" "main" {
  name                = "adf-${var.project_name}-${var.environment}"
  location            = var.location
  resource_group_name = var.resource_group_name
  tags                = var.tags

  identity {
    type = "SystemAssigned"
  }

  # Git integration — pipelines live in lakehouse-app/adf/ in the same repo.
  # Omitted when devops_account_name is not supplied (e.g. personal forks).
  dynamic "vsts_configuration" {
    for_each = var.devops_account_name != "" ? [1] : []
    content {
      account_name    = var.devops_account_name
      branch_name     = "main"
      project_name    = var.devops_project_name
      repository_name = var.app_repo_name
      root_folder     = "/adf"
      tenant_id       = var.tenant_id
    }
  }
}

# ── Linked services ────────────────────────────────────────────────────────────

resource "azurerm_data_factory_linked_service_key_vault" "kv" {
  name            = "ls-keyvault-${var.environment}"
  data_factory_id = azurerm_data_factory.main.id
  key_vault_id    = var.key_vault_id
}

# Linked service to Functions — only created when function_app_url is supplied.
resource "azurerm_data_factory_linked_service_azure_function" "functions" {
  count           = var.function_app_url != null ? 1 : 0
  name            = "ls-functions-${var.environment}"
  data_factory_id = azurerm_data_factory.main.id
  url             = var.function_app_url
}

# ── Diagnostic setting → Log Analytics ────────────────────────────────────────

resource "azurerm_monitor_diagnostic_setting" "adf" {
  count                      = var.log_analytics_workspace_id != null ? 1 : 0
  name                       = "diag-adf-${var.environment}"
  target_resource_id         = azurerm_data_factory.main.id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  enabled_log { category = "ActivityRuns" }
  enabled_log { category = "PipelineRuns" }
  enabled_log { category = "TriggerRuns" }
  metric { category = "AllMetrics" }
}
