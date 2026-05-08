# RBAC role assignments for all compute managed identities.
# All assignments are gated on deploy_expensive_resources = true because the
# compute modules that produce the principal_ids are themselves gated.
#
# Role assignment map (Phase 2 spec):
#   ADF MI      → Key Vault Secrets User  (Key Vault)
#   ADF MI      → Storage Blob Data Contributor  (bronze, silver)
#   Functions MI → Key Vault Secrets User  (Key Vault)
#   Functions MI → Storage Blob Data Contributor  (bronze)
#   Synapse MI  → Key Vault Secrets User  (Key Vault)
#   Synapse MI  → Storage Blob Data Contributor  (bronze, silver, gold, quarantine)
#   AAS MI      → Storage Blob Data Reader  (gold)
#
# DevOps SP → Artifacts Contributor on lakehouse-feed is an Azure DevOps
# Artifacts permission, not an Azure RBAC assignment — configured manually.
# Synapse MI → Artifacts Reader on lakehouse-feed is similarly ADO-side.

locals {
  # Flatten all compute principal_ids once — each is null until its phase deploys.
  adf_principal_id      = var.deploy_expensive_resources ? module.data_factory[0].principal_id : null
  func_principal_id     = var.deploy_expensive_resources ? module.functions[0].principal_id : null
  synapse_principal_id  = var.deploy_expensive_resources ? module.synapse[0].principal_id : null
  aas_principal_id      = var.deploy_expensive_resources ? module.analysis_services[0].principal_id : null
}

# ── ADF role assignments ───────────────────────────────────────────────────────

resource "azurerm_role_assignment" "adf_kv_secrets_user" {
  count = local.adf_principal_id != null ? 1 : 0

  scope                = module.key_vault.key_vault_id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = local.adf_principal_id
}

resource "azurerm_role_assignment" "adf_storage_bronze" {
  count = local.adf_principal_id != null ? 1 : 0

  scope                = module.storage.bronze_filesystem_id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = local.adf_principal_id
}

resource "azurerm_role_assignment" "adf_storage_silver" {
  count = local.adf_principal_id != null ? 1 : 0

  scope                = module.storage.silver_filesystem_id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = local.adf_principal_id
}

# ── Functions role assignments ─────────────────────────────────────────────────

resource "azurerm_role_assignment" "func_kv_secrets_user" {
  count = local.func_principal_id != null ? 1 : 0

  scope                = module.key_vault.key_vault_id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = local.func_principal_id
}

resource "azurerm_role_assignment" "func_storage_bronze" {
  count = local.func_principal_id != null ? 1 : 0

  scope                = module.storage.bronze_filesystem_id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = local.func_principal_id
}

# ── Synapse role assignments ───────────────────────────────────────────────────

resource "azurerm_role_assignment" "synapse_kv_secrets_user" {
  count = local.synapse_principal_id != null ? 1 : 0

  scope                = module.key_vault.key_vault_id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = local.synapse_principal_id
}

resource "azurerm_role_assignment" "synapse_storage_bronze" {
  count = local.synapse_principal_id != null ? 1 : 0

  scope                = module.storage.bronze_filesystem_id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = local.synapse_principal_id
}

resource "azurerm_role_assignment" "synapse_storage_silver" {
  count = local.synapse_principal_id != null ? 1 : 0

  scope                = module.storage.silver_filesystem_id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = local.synapse_principal_id
}

resource "azurerm_role_assignment" "synapse_storage_gold" {
  count = local.synapse_principal_id != null ? 1 : 0

  scope                = module.storage.gold_filesystem_id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = local.synapse_principal_id
}

resource "azurerm_role_assignment" "synapse_storage_quarantine" {
  count = local.synapse_principal_id != null ? 1 : 0

  scope                = module.storage.quarantine_filesystem_id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = local.synapse_principal_id
}

# ── AAS role assignments ───────────────────────────────────────────────────────

resource "azurerm_role_assignment" "aas_storage_gold_reader" {
  count = local.aas_principal_id != null ? 1 : 0

  scope                = module.storage.gold_filesystem_id
  role_definition_name = "Storage Blob Data Reader"
  principal_id         = local.aas_principal_id
}
