output "data_factory_id" {
  description = "Resource ID of the Azure Data Factory instance."
  value       = azurerm_data_factory.main.id
}

output "principal_id" {
  description = "Principal ID of the ADF system-assigned managed identity."
  value       = azurerm_data_factory.main.identity[0].principal_id
}
