output "function_app_id" {
  description = "Resource ID of the Azure Function App."
  value       = azurerm_linux_function_app.main.id
}

output "function_app_hostname" {
  description = "Default hostname of the Function App (e.g. func-lakehouse-dev.azurewebsites.net)."
  value       = azurerm_linux_function_app.main.default_hostname
}

output "principal_id" {
  description = "Principal ID of the Function App system-assigned managed identity."
  value       = azurerm_linux_function_app.main.identity[0].principal_id
}
