output "key_vault_id" {
  description = "Resource ID of the Key Vault."
  value       = azurerm_key_vault.main.id
}

output "key_vault_uri" {
  description = "URI of the Key Vault (used by app code as KEY_VAULT_URL)."
  value       = azurerm_key_vault.main.vault_uri
}

output "key_vault_name" {
  description = "Name of the Key Vault."
  value       = azurerm_key_vault.main.name
}

output "secret_ids" {
  description = "Map of secret name to secret resource ID for each managed secret."
  value       = { for k, v in azurerm_key_vault_secret.secrets : k => v.id }
}
