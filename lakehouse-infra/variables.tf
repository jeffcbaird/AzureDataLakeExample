# ── Core ──────────────────────────────────────────────────────────────────────

variable "subscription_id" {
  description = "Azure subscription ID to deploy resources into."
  type        = string
}

variable "tenant_id" {
  description = "Azure Active Directory tenant ID."
  type        = string
}

variable "location" {
  description = "Azure region for all resources (e.g. westus2, australiaeast)."
  type        = string
  default     = "westus2"
}

variable "environment" {
  description = "Deployment environment: dev or prod."
  type        = string
  validation {
    condition     = contains(["dev", "prod"], var.environment)
    error_message = "environment must be one of: dev, prod."
  }
}

variable "project_name" {
  description = "Short project name used in resource naming."
  type        = string
  default     = "lakehouse"
}

variable "tags" {
  description = "Tags applied to all resources."
  type        = map(string)
  default     = {}
}

# ── Example project budget constraint ─────────────────────────────────────────

variable "deploy_expensive_resources" {
  description = <<-EOT
    Controls whether cost-significant resources are provisioned.
    Must remain false for the example project (Azure spend cap: $1/month).
    Remove the validation block below before setting to true in production.
  EOT
  type    = bool
  default = false

  validation {
    condition     = !var.deploy_expensive_resources
    error_message = "This is an example project with a $1/month spend cap. Remove this validation block before deploying to production."
  }
}

# ── Analysis Services ─────────────────────────────────────────────────────────

variable "aas_admin_users" {
  description = "List of UPNs granted admin access to Analysis Services (prod only)."
  type        = list(string)
  default     = []
}

# ── Azure DevOps — used by ADF Git integration ────────────────────────────────

variable "devops_account_name" {
  description = "Azure DevOps organization name (e.g. 'myorg'). Leave empty to skip ADF Git integration."
  type        = string
  default     = ""
}

variable "devops_project_name" {
  description = "Azure DevOps project name containing the lakehouse-app repository."
  type        = string
  default     = "lakehouse"
}

# ── Monitoring ────────────────────────────────────────────────────────────────

variable "alert_webhook_url" {
  description = "Teams or Slack incoming webhook URL for Monitor action group alerts. Leave empty to skip webhook receiver."
  type        = string
  default     = ""
}

variable "source_names" {
  description = "List of ingestion source names (e.g. [\"sales\", \"inventory\", \"partner-drops\"]) used to scope the bronze file-absence alert."
  type        = list(string)
  default     = []
}
