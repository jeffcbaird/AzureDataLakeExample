variable "resource_group_name" {
  type = string
}
variable "location" {
  type = string
}
variable "environment" {
  type = string
}
variable "project_name" {
  type = string
}
variable "tags" {
  type = map(string)
}
variable "alert_webhook_url" {
  type    = string
  default = ""
}
variable "source_names" {
  type    = list(string)
  default = []
}

variable "function_app_id" {
  description = "Resource ID of the Function App — used for the Functions error-rate metric alert. Null when functions are not deployed."
  type        = string
  default     = null
}

variable "synapse_serverless_endpoint" {
  description = "Synapse Analytics Serverless SQL endpoint URL — injected into the workbook for Gold freshness queries. Empty string until Phase 5."
  type        = string
  default     = ""
}

variable "synapse_workspace_resource_id" {
  description = "ARM resource ID of the Synapse workspace — used by the workbook to scope Serverless SQL queries for DQ violations and tier row counts."
  type        = string
  default     = ""
}
