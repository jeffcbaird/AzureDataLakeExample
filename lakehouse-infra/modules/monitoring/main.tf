# Azure Monitor — Log Analytics workspace, action group, alerts, and workbook.

# ── Log Analytics workspace ────────────────────────────────────────────────────

resource "azurerm_log_analytics_workspace" "main" {
  name                = "log-${var.project_name}-${var.environment}"
  location            = var.location
  resource_group_name = var.resource_group_name
  sku                 = "PerGB2018"
  retention_in_days   = 30   # 5 GB/day ingestion is free; minimum retention is 30 days
  tags                = var.tags
}

# ── Action group — Teams/Slack webhook ────────────────────────────────────────

resource "azurerm_monitor_action_group" "main" {
  name                = "ag-${var.project_name}-${var.environment}"
  resource_group_name = var.resource_group_name
  short_name          = "lakehouse"
  tags                = var.tags

  dynamic "webhook_receiver" {
    for_each = var.alert_webhook_url != "" ? [1] : []
    content {
      name                    = "teams-webhook"
      service_uri             = var.alert_webhook_url
      use_common_alert_schema = true
    }
  }
}

# ── Alert: ADF pipeline failure rate > 5 % over 1 h ──────────────────────────

resource "azurerm_monitor_scheduled_query_rules_alert_v2" "adf_failure_rate" {
  name                = "alert-adf-failure-rate-${var.environment}"
  location            = var.location
  resource_group_name = var.resource_group_name
  tags                = var.tags

  evaluation_frequency = "PT1H"
  window_duration      = "PT1H"
  scopes               = [azurerm_log_analytics_workspace.main.id]
  severity             = 2   # Warning

  criteria {
    query = <<-KQL
      ADFPipelineRun
      | where TimeGenerated > ago(1h)
      | summarize total = count(), failed = countif(Status == "Failed")
      | where total > 0
      | extend failure_rate = todouble(failed) / total * 100
      | where failure_rate > 5
    KQL
    time_aggregation_method = "Count"
    threshold               = 0
    operator                = "GreaterThan"
  }

  action {
    action_groups = [azurerm_monitor_action_group.main.id]
  }
}

# ── Alert: Function App error rate ────────────────────────────────────────────

resource "azurerm_monitor_metric_alert" "functions_errors" {
  count               = var.function_app_id != null ? 1 : 0
  name                = "alert-func-errors-${var.environment}"
  resource_group_name = var.resource_group_name
  scopes              = [var.function_app_id]
  description         = "Function App failure executions exceeded threshold."
  severity            = 2
  tags                = var.tags

  criteria {
    metric_namespace = "Microsoft.Web/sites"
    metric_name      = "FunctionExecutionCount"
    aggregation      = "Count"
    operator         = "GreaterThan"
    threshold        = 10

    dimension {
      name     = "Status"
      operator = "Include"
      values   = ["Failed"]
    }
  }

  action {
    action_group_id = azurerm_monitor_action_group.main.id
  }
}

# ── Alert: Bronze file absence per source ─────────────────────────────────────

resource "azurerm_monitor_scheduled_query_rules_alert_v2" "bronze_file_absence" {
  count               = length(var.source_names) > 0 ? 1 : 0
  name                = "alert-bronze-absence-${var.environment}"
  location            = var.location
  resource_group_name = var.resource_group_name
  tags                = var.tags

  description          = "Expected bronze write from one or more sources has not appeared within 6 hours."
  evaluation_frequency = "PT1H"
  window_duration      = "PT6H"
  scopes               = [azurerm_log_analytics_workspace.main.id]
  severity             = 1   # Error

  criteria {
    query = <<-KQL
      StorageBlobLogs
      | where TimeGenerated > ago(6h)
      | where OperationName == "PutBlob" or OperationName == "PutBlock"
      | where Uri contains "/bronze/"
      | summarize last_write = max(TimeGenerated) by tostring(split(Uri, "/")[3])
      | where last_write < ago(6h)
    KQL
    time_aggregation_method = "Count"
    threshold               = 0
    operator                = "GreaterThan"
  }

  action {
    action_groups = [azurerm_monitor_action_group.main.id]
  }
}

# ── Alert: AAS heartbeat absence — placeholder, enabled in Phase 7 ────────────

resource "azurerm_monitor_scheduled_query_rules_alert_v2" "aas_heartbeat" {
  name                = "alert-aas-heartbeat-${var.environment}"
  location            = var.location
  resource_group_name = var.resource_group_name
  tags                = var.tags

  description          = "Azure Analysis Services has produced no diagnostic heartbeat. Activates Phase 7."
  evaluation_frequency = "PT1H"
  window_duration      = "PT1H"
  scopes               = [azurerm_log_analytics_workspace.main.id]
  severity             = 2
  enabled              = false   # set to true in Phase 7 when AAS is provisioned

  criteria {
    query = <<-KQL
      AzureDiagnostics
      | where ResourceType == "ANALYSISSERVICES/SERVERS"
      | summarize heartbeats = count()
      | where heartbeats == 0
    KQL
    time_aggregation_method = "Count"
    threshold               = 0
    operator                = "GreaterThan"
  }

  action {
    action_groups = [azurerm_monitor_action_group.main.id]
  }
}

# ── Workbook — four-panel operations dashboard ────────────────────────────────

resource "azurerm_application_insights_workbook" "main" {
  # Stable deterministic GUID — safe to keep fixed across environments.
  name                = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
  resource_group_name = var.resource_group_name
  location            = var.location
  display_name        = "Lakehouse — ${var.environment} Operations"
  tags                = var.tags

  data_json = templatefile("${path.module}/workbook.json", {
    workspace_id                  = azurerm_log_analytics_workspace.main.id
    synapse_serverless_endpoint   = var.synapse_serverless_endpoint
    synapse_workspace_resource_id = var.synapse_workspace_resource_id
    environment                   = var.environment
  })
}
