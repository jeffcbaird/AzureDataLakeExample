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
variable "artifacts_feed_url" {
  type    = string
  default = ""
}

variable "key_vault_uri" {
  description = "URI of the Key Vault used for app settings KV references (e.g. https://kv-lakehouse-dev.vault.azure.net/)."
  type        = string
  default     = ""
}

variable "log_analytics_workspace_id" {
  description = "Resource ID of the Log Analytics workspace for diagnostic settings. Null when monitoring module is not deployed."
  type        = string
  default     = null
}
