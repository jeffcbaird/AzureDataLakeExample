# ── Synapse workspace ─────────────────────────────────────────────────────────

locals {
  workspace_name = "syn-${var.project_name}-${var.environment}"
  pool_name      = "sparkpool"
}

# Pull the SQL admin password from Key Vault so it is never in state plaintext.
data "azurerm_key_vault_secret" "synapse_sql_admin" {
  name         = "synapse-sql-admin-password"
  key_vault_id = var.key_vault_id
}

resource "azurerm_synapse_workspace" "main" {
  name                                 = local.workspace_name
  resource_group_name                  = var.resource_group_name
  location                             = var.location
  storage_data_lake_gen2_filesystem_id = var.storage_data_lake_gen2_filesystem_id
  sql_administrator_login              = var.sql_administrator_login
  sql_administrator_login_password     = data.azurerm_key_vault_secret.synapse_sql_admin.value

  identity {
    type = "SystemAssigned"
  }

  tags = var.tags
}

# ── Firewall rules ────────────────────────────────────────────────────────────

# Allow all Azure services (start/end 0.0.0.0 is the Azure-services sentinel).
resource "azurerm_synapse_firewall_rule" "azure_services" {
  name                 = "AllowAzureServices"
  synapse_workspace_id = azurerm_synapse_workspace.main.id
  start_ip_address     = "0.0.0.0"
  end_ip_address       = "0.0.0.0"
}

# Optional: allow caller-supplied CIDR ranges (e.g. developer workstations, VPN).
resource "azurerm_synapse_firewall_rule" "allowed_ranges" {
  count                = length(var.allowed_ip_ranges)
  name                 = "Allow-${count.index}"
  synapse_workspace_id = azurerm_synapse_workspace.main.id
  start_ip_address     = cidrhost(var.allowed_ip_ranges[count.index], 0)
  end_ip_address       = cidrhost(var.allowed_ip_ranges[count.index], -1)
}

# ── Spark pool ────────────────────────────────────────────────────────────────

resource "azurerm_synapse_spark_pool" "main" {
  name                 = local.pool_name
  synapse_workspace_id = azurerm_synapse_workspace.main.id
  node_size_family     = "MemoryOptimized"
  node_size            = "Small"

  auto_scale {
    min_node_count = 3
    max_node_count = var.spark_max_node_count
  }

  auto_pause {
    delay_in_minutes = 10
  }

  # Upload lakehouse-common[spark] and its dependencies to the pool.
  library_requirement {
    content  = file("${path.module}/spark_requirements.txt")
    filename = "requirements.txt"
  }

  tags = var.tags
}

# ── Diagnostic setting ────────────────────────────────────────────────────────

resource "azurerm_monitor_diagnostic_setting" "synapse" {
  count                      = var.log_analytics_workspace_id != null ? 1 : 0
  name                       = "diag-synapse-${var.environment}"
  target_resource_id         = azurerm_synapse_workspace.main.id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  enabled_log { category = "SynapseRbacOperations" }
  enabled_log { category = "GatewayApiRequests" }
  enabled_log { category = "BuiltinSqlReqsEnded" }
  enabled_log { category = "IntegrationPipelineRuns" }

  metric {
    category = "AllMetrics"
  }
}

# ── Power BI service firewall rules ───────────────────────────────────────────
# Allow the Power BI service to query Synapse Serverless SQL.
# IP ranges sourced from Microsoft's published Power BI allow-list.

locals {
  power_bi_ranges = var.enable_power_bi_firewall_rules ? [
    { name = "pbi-global-1",  start = "13.64.176.0",  end = "13.64.191.255" },
    { name = "pbi-global-2",  start = "40.74.128.0",  end = "40.74.143.255" },
    { name = "pbi-westus2-1", start = "20.42.128.0",  end = "20.42.135.255" },
    { name = "pbi-westus2-2", start = "20.42.0.0",    end = "20.42.7.255"   },
  ] : []
}

resource "azurerm_synapse_firewall_rule" "power_bi" {
  for_each             = { for r in local.power_bi_ranges : r.name => r }
  name                 = each.value.name
  synapse_workspace_id = azurerm_synapse_workspace.main.id
  start_ip_address     = each.value.start
  end_ip_address       = each.value.end
}
