"""Integration test fixtures.

These tests require Azure credentials (DefaultAzureCredential) and a live Key
Vault. They are skipped automatically when KEY_VAULT_URL is not set so they
never block local unit-test runs.

In CI the ``run-integration-tests.yml`` pipeline sets KEY_VAULT_URL from a
pipeline variable and runs every 15 minutes against the dev environment.
"""
from __future__ import annotations

import os

import pytest

from lakehouse_common.keyvault.client import get_secret


# ── Custom marker ─────────────────────────────────────────────────────────────

def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "integration: marks tests that require live Azure credentials",
    )


# ── Skip guard ────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session", autouse=True)
def require_keyvault() -> None:
    """Skip the entire integration suite if KEY_VAULT_URL is not configured."""
    if not os.environ.get("KEY_VAULT_URL"):
        pytest.skip(
            "KEY_VAULT_URL not set — skipping integration tests. "
            "Set KEY_VAULT_URL=https://<vault>.vault.azure.net/ to run."
        )


# ── API source credentials ─────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def sales_api_key() -> str:
    return get_secret("sales-api-key")


@pytest.fixture(scope="session")
def sales_api_base_url() -> str:
    return os.environ.get("SALES_API_BASE_URL", "https://api.example-sales.com/v1")


@pytest.fixture(scope="session")
def inventory_api_key() -> str:
    return get_secret("inventory-api-key")


@pytest.fixture(scope="session")
def inventory_api_base_url() -> str:
    return os.environ.get("INVENTORY_API_BASE_URL", "https://api.example-inventory.com/v2")


# ── FTP source credentials ────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def partner_ftp_creds() -> dict:
    return {
        "host":     get_secret("ftp-partner-drops-host"),
        "username": get_secret("ftp-partner-drops-username"),
        "password": get_secret("ftp-partner-drops-password"),
    }
