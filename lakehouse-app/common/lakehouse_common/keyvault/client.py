"""Key Vault client — get_secret() and list_secrets() using DefaultAzureCredential."""
from __future__ import annotations

import os
from functools import lru_cache

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient


@lru_cache(maxsize=1)
def _client() -> SecretClient:
    url = os.environ["KEY_VAULT_URL"]
    return SecretClient(vault_url=url, credential=DefaultAzureCredential())


def get_secret(name: str) -> str:
    """Retrieve a secret value by name. Raises KeyError if not found."""
    secret = _client().get_secret(name)
    if secret.value is None:
        raise KeyError(f"Secret '{name}' exists but has no value.")
    return secret.value


def list_secrets() -> list[str]:
    """Return a list of all secret names in the vault."""
    return [s.name for s in _client().list_properties_of_secrets()]
