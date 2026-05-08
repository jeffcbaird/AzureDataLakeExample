output "synapse_workspace_id" {
  description = "Resource ID of the Synapse workspace."
  value       = azurerm_synapse_workspace.main.id
}

output "synapse_serverless_sql_endpoint" {
  description = "Serverless SQL (on-demand) endpoint for the Synapse workspace."
  value       = azurerm_synapse_workspace.main.connectivity_endpoints["sqlOnDemand"]
}

output "principal_id" {
  description = "Principal ID of the Synapse system-assigned managed identity."
  value       = azurerm_synapse_workspace.main.identity[0].principal_id
}

output "spark_pool_id" {
  description = "Resource ID of the Spark pool."
  value       = azurerm_synapse_spark_pool.main.id
}
