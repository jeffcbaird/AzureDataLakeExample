"""Function-app-local Key Vault helper.

Uses DefaultAzureCredential so the same code works with the Function App's
managed identity in Azure and with ``az login`` / env vars locally.
"""
from __future__ import annotations

import os
from functools import lru_cache

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient


@lru_cache(maxsize=1)
def _client() -> SecretClient:
    uri = os.environ["KEYVAULT_URI"]
    return SecretClient(vault_url=uri, credential=DefaultAzureCredential())


def get_secret(name: str) -> str:
    """Return the current value of *name* from Key Vault.

    The SecretClient caches the credential internally; call this freely
    without worrying about per-request token overhead.
    """
    return _client().get_secret(name).value
