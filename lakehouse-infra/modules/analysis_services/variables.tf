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
variable "sku" {
  type        = string
  default     = "D1"
  description = "AAS SKU — D1 (dev/free tier) or S0/S1/S2/S4 (prod)."
}
variable "admin_users" {
  type        = list(string)
  default     = []
  description = "UPNs of Analysis Services administrators (e.g. 'user@domain.com')."
}
variable "tags" {
  type = map(string)
}
variable "allowed_ip_ranges" {
  type        = list(string)
  default     = []
  description = "Additional CIDR ranges permitted through the AAS firewall (e.g. developer IPs)."
}
variable "enable_power_bi_service_ips" {
  type        = bool
  default     = true
  description = "When true, adds firewall rules for the well-known Power BI service IP ranges."
}
