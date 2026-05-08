output "workspace_id" {
  description = "Resource ID of the Log Analytics workspace — passed to diagnostic settings."
  value       = azurerm_log_analytics_workspace.main.id
}

output "workspace_resource_id" {
  description = "Full resource ID of the Log Analytics workspace (alias of workspace_id)."
  value       = azurerm_log_analytics_workspace.main.id
}

output "action_group_id" {
  description = "Resource ID of the Monitor action group."
  value       = azurerm_monitor_action_group.main.id
}
