output "storage_account_name" {
  description = "Name of the ADLS Gen2 storage account."
  value       = azurerm_storage_account.adls.name
}

output "storage_account_id" {
  description = "Resource ID of the ADLS Gen2 storage account."
  value       = azurerm_storage_account.adls.id
}

output "adls_primary_dfs_endpoint" {
  description = "Primary DFS endpoint URL."
  value       = azurerm_storage_account.adls.primary_dfs_endpoint
}

output "bronze_abfss_uri" {
  description = "abfss URI for the bronze container."
  value       = local.bronze_abfss_uri
}

output "silver_abfss_uri" {
  description = "abfss URI for the silver container."
  value       = local.silver_abfss_uri
}

output "gold_abfss_uri" {
  description = "abfss URI for the gold container."
  value       = local.gold_abfss_uri
}

output "quarantine_abfss_uri" {
  description = "abfss URI for the quarantine container."
  value       = local.quarantine_abfss_uri
}

output "dq_results_abfss_uri" {
  description = "abfss URI for the silver/dq_results/ managed Delta table."
  value       = local.dq_results_abfss_uri
}

output "table_registry_abfss_uri" {
  description = "abfss URI for the silver/_table_registry/ managed Delta table."
  value       = local.table_registry_abfss_uri
}

output "bronze_filesystem_id" {
  value = azurerm_storage_data_lake_gen2_filesystem.bronze.id
}

output "silver_filesystem_id" {
  value = azurerm_storage_data_lake_gen2_filesystem.silver.id
}

output "gold_filesystem_id" {
  value = azurerm_storage_data_lake_gen2_filesystem.gold.id
}

output "quarantine_filesystem_id" {
  value = azurerm_storage_data_lake_gen2_filesystem.quarantine.id
}
