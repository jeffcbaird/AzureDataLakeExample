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
  type        = string
  description = "Resource ID of the Key Vault that holds the Synapse SQL admin password."
}
variable "adls_primary_dfs_endpoint" {
  type        = string
  description = "Primary DFS endpoint of the ADLS Gen2 account (used only as a reference; filesystem_id drives auth)."
}
variable "storage_data_lake_gen2_filesystem_id" {
  type        = string
  description = "Resource ID of the ADLS Gen2 filesystem (container) used as Synapse's default data lake store."
}
variable "log_analytics_workspace_id" {
  type    = string
  default = null
}
variable "tags" {
  type = map(string)
}
variable "spark_max_node_count" {
  type    = number
  default = 5
}
variable "sql_administrator_login" {
  type        = string
  default     = "sqladmin"
  description = "SQL administrator login name for the Synapse workspace."
}
variable "allowed_ip_ranges" {
  type        = list(string)
  default     = []
  description = "Optional list of CIDR ranges permitted through the Synapse firewall (in addition to Azure services)."
}
variable "enable_power_bi_firewall_rules" {
  type        = bool
  default     = true
  description = "When true, adds Synapse firewall rules for Power BI service IP ranges so Serverless SQL is reachable from Power BI."
}
