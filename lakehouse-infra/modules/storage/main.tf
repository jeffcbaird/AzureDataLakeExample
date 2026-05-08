# Phase 1 implementation. See Plan.md for full specification.

locals {
  name_prefix  = "${var.project_name}${var.environment}"
  account_name = "st${var.project_name}${var.environment}adls"
}

locals {
  bronze_abfss_uri         = "abfss://bronze@${local.account_name}.dfs.core.windows.net"
  silver_abfss_uri         = "abfss://silver@${local.account_name}.dfs.core.windows.net"
  gold_abfss_uri           = "abfss://gold@${local.account_name}.dfs.core.windows.net"
  quarantine_abfss_uri     = "abfss://quarantine@${local.account_name}.dfs.core.windows.net"
  dq_results_abfss_uri     = "abfss://silver@${local.account_name}.dfs.core.windows.net/dq_results"
  table_registry_abfss_uri = "abfss://silver@${local.account_name}.dfs.core.windows.net/_table_registry"
}

resource "azurerm_storage_account" "adls" {
  name                     = "st${local.name_prefix}adls"
  resource_group_name      = var.resource_group_name
  location                 = var.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  account_kind             = "StorageV2"
  is_hns_enabled           = true
  min_tls_version          = "TLS1_2"

  blob_properties {
    delete_retention_policy {
      days = 7
    }
    container_delete_retention_policy {
      days = 7
    }
  }

  tags = var.tags
}

resource "azurerm_storage_data_lake_gen2_filesystem" "bronze" {
  name               = "bronze"
  storage_account_id = azurerm_storage_account.adls.id
}

resource "azurerm_storage_data_lake_gen2_filesystem" "silver" {
  name               = "silver"
  storage_account_id = azurerm_storage_account.adls.id
}

resource "azurerm_storage_data_lake_gen2_filesystem" "gold" {
  name               = "gold"
  storage_account_id = azurerm_storage_account.adls.id
}

resource "azurerm_storage_data_lake_gen2_filesystem" "quarantine" {
  name               = "quarantine"
  storage_account_id = azurerm_storage_account.adls.id
}

resource "azurerm_storage_management_policy" "lifecycle" {
  storage_account_id = azurerm_storage_account.adls.id

  rule {
    name    = "bronze-cool-after-90d"
    enabled = true
    filters {
      prefix_match = ["bronze/"]
      blob_types   = ["blockBlob"]
    }
    actions {
      base_blob {
        tier_to_cool_after_days_since_modification_greater_than = 90
      }
    }
  }
}

resource "azurerm_monitor_diagnostic_setting" "storage" {
  count = var.log_analytics_workspace_id != null ? 1 : 0

  name                       = "diag-storage-${var.environment}"
  target_resource_id         = azurerm_storage_account.adls.id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  metric {
    category = "Transaction"
  }
}
