variable "resource_group_name" { type = string }
variable "location"            { type = string }
variable "environment"         { type = string }
variable "project_name"        { type = string }
variable "tenant_id"           { type = string }
variable "tags"                { type = map(string) }
variable "secrets" {
  description = "Map of secret name => value to store in Key Vault."
  type        = map(string)
  default     = {}
  sensitive   = true
}
