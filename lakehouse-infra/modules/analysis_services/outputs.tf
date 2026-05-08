output "aas_server_name" {
  description = "Name of the Analysis Services server."
  value       = azurerm_analysis_services_server.main.name
}

output "aas_server_full_name" {
  description = "Fully-qualified server name used as the data source in Power BI / TMSL (asazure://region/servername)."
  value       = azurerm_analysis_services_server.main.server_full_name
}

output "principal_id" {
  description = "Managed identity principal ID (AAS uses a system-assigned identity when available; otherwise null)."
  # azurerm_analysis_services_server does not expose a managed identity — return null.
  value = null
}
