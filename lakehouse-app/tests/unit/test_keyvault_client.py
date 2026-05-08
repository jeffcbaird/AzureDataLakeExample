"""Unit tests for lakehouse_common.keyvault.client.

All Azure SDK calls are mocked so these tests run without any Azure credentials
or network access.
"""
from __future__ import annotations

import importlib
import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_secret_property(name: str):
    """Build a minimal SecretProperties-like object."""
    prop = SimpleNamespace(name=name)
    return prop


def _make_secret(name: str, value: str):
    """Build a minimal KeyVaultSecret-like object."""
    return SimpleNamespace(name=name, value=value)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_client_cache():
    """Clear the lru_cache between tests so each test gets a fresh client."""
    # Import fresh each time so the cache is independent per test
    import lakehouse_common.keyvault.client as mod
    mod._client.cache_clear()
    yield
    mod._client.cache_clear()


@pytest.fixture()
def mock_secret_client(monkeypatch):
    """Patch SecretClient and DefaultAzureCredential; return the mock client."""
    monkeypatch.setenv("KEY_VAULT_URL", "https://kv-test.vault.azure.net/")

    mock_client = MagicMock()

    with patch("lakehouse_common.keyvault.client.DefaultAzureCredential"), \
         patch("lakehouse_common.keyvault.client.SecretClient", return_value=mock_client):
        import lakehouse_common.keyvault.client as mod
        mod._client.cache_clear()
        yield mock_client


# ---------------------------------------------------------------------------
# get_secret
# ---------------------------------------------------------------------------

class TestGetSecret:
    def test_returns_secret_value(self, mock_secret_client):
        mock_secret_client.get_secret.return_value = _make_secret("db-password", "s3cr3t")

        from lakehouse_common.keyvault import client
        result = client.get_secret("db-password")

        assert result == "s3cr3t"
        mock_secret_client.get_secret.assert_called_once_with("db-password")

    def test_raises_key_error_when_value_is_none(self, mock_secret_client):
        mock_secret_client.get_secret.return_value = _make_secret("empty-secret", None)

        from lakehouse_common.keyvault import client
        with pytest.raises(KeyError, match="empty-secret"):
            client.get_secret("empty-secret")

    def test_propagates_sdk_exception(self, mock_secret_client):
        mock_secret_client.get_secret.side_effect = RuntimeError("vault unreachable")

        from lakehouse_common.keyvault import client
        with pytest.raises(RuntimeError, match="vault unreachable"):
            client.get_secret("any-secret")

    def test_missing_env_var_raises(self, monkeypatch):
        monkeypatch.delenv("KEY_VAULT_URL", raising=False)

        import lakehouse_common.keyvault.client as mod
        mod._client.cache_clear()

        with patch("lakehouse_common.keyvault.client.DefaultAzureCredential"), \
             patch("lakehouse_common.keyvault.client.SecretClient") as mock_cls:
            mock_cls.side_effect = KeyError("KEY_VAULT_URL")
            from lakehouse_common.keyvault import client
            with pytest.raises((KeyError, Exception)):
                client.get_secret("x")


# ---------------------------------------------------------------------------
# list_secrets
# ---------------------------------------------------------------------------

class TestListSecrets:
    def test_returns_list_of_names(self, mock_secret_client):
        mock_secret_client.list_properties_of_secrets.return_value = [
            _make_secret_property("api-key"),
            _make_secret_property("db-password"),
            _make_secret_property("storage-key"),
        ]

        from lakehouse_common.keyvault import client
        result = client.list_secrets()

        assert result == ["api-key", "db-password", "storage-key"]

    def test_returns_empty_list_when_vault_is_empty(self, mock_secret_client):
        mock_secret_client.list_properties_of_secrets.return_value = []

        from lakehouse_common.keyvault import client
        result = client.list_secrets()

        assert result == []

    def test_propagates_sdk_exception(self, mock_secret_client):
        mock_secret_client.list_properties_of_secrets.side_effect = RuntimeError("auth failed")

        from lakehouse_common.keyvault import client
        with pytest.raises(RuntimeError, match="auth failed"):
            client.list_secrets()
