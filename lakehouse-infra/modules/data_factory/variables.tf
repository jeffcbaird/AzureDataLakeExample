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
variable "key_vault_id" {
  type = string
}
variable "storage_account_id" {
  type = string
}
variable "tags" {
  type = map(string)
}
variable "app_repo_name" {
  type    = string
  default = "lakehouse-app"
}
variable "devops_project_name" {
  type    = string
  default = "lakehouse"
}
variable "devops_account_name" {
  type    = string
  default = ""
}

variable "tenant_id" {
  description = "Azure AD tenant ID — required for ADF Git integration."
  type        = string
  default     = ""
}

variable "function_app_url" {
  description = "HTTPS URL of the Function App. When set, an ADF linked service is created."
  type        = string
  default     = null
}

variable "log_analytics_workspace_id" {
  description = "Resource ID of the Log Analytics workspace for diagnostic settings. Null when monitoring module is not deployed."
  type        = string
  default     = null
}
