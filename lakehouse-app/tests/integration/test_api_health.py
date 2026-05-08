"""Integration tests — REST API source health checks.

Each test authenticates to a source API using the same credential path used
in production (Key Vault → API key → Authorization header) and makes a
lightweight request to verify connectivity. Tests are designed to be fast
(< 5 seconds each) and non-destructive (read-only, no writes).

A test failure here means either:
  - The source API is unreachable or returning errors, OR
  - The Key Vault secret has expired / been rotated without updating ADF.

Both cases require immediate investigation — this suite runs every 15 minutes
via ``run-integration-tests.yml``.
"""
from __future__ import annotations

import pytest
import requests

from lakehouse_common.clients.base_http import ApiKeyAuth, BaseHttpClient

pytestmark = pytest.mark.integration


# ── Lightweight probe clients ─────────────────────────────────────────────────

class _ProbeClient(BaseHttpClient):
    """One-shot HTTP client for connectivity probing."""

    def __init__(self, base_url: str, api_key: str, header: str = "X-Api-Key") -> None:
        self.BASE_URL = base_url
        super().__init__(auth=ApiKeyAuth(header, api_key), timeout=10)


# ── Sales API ─────────────────────────────────────────────────────────────────

class TestSalesApiHealth:
    def test_authenticated_request_succeeds(
        self, sales_api_key: str, sales_api_base_url: str
    ) -> None:
        """A GET to /health (or equivalent) with a valid API key must return 2xx."""
        client = _ProbeClient(sales_api_base_url, sales_api_key)
        # Prefer a dedicated /health endpoint; fall back to listing with limit=1.
        try:
            resp = client.get("/health")
        except requests.HTTPError:
            resp = client.get("/orders", params={"limit": 1})
        assert resp.status_code < 300, (
            f"Sales API returned {resp.status_code}: {resp.text[:200]}"
        )

    def test_invalid_key_returns_401(self, sales_api_base_url: str) -> None:
        """A request with a bogus API key must be rejected with 401 or 403."""
        client = _ProbeClient(sales_api_base_url, "invalid-key-probe")
        with pytest.raises(requests.HTTPError) as exc_info:
            client.get("/health")
        assert exc_info.value.response.status_code in (401, 403), (
            "Expected 401/403 for invalid key, "
            f"got {exc_info.value.response.status_code}"
        )


# ── Inventory API ─────────────────────────────────────────────────────────────

class TestInventoryApiHealth:
    def test_authenticated_request_succeeds(
        self, inventory_api_key: str, inventory_api_base_url: str
    ) -> None:
        """A GET to /health with a valid API key must return 2xx."""
        client = _ProbeClient(inventory_api_base_url, inventory_api_key)
        try:
            resp = client.get("/health")
        except requests.HTTPError:
            resp = client.get("/snapshots", params={"page_size": 1})
        assert resp.status_code < 300, (
            f"Inventory API returned {resp.status_code}: {resp.text[:200]}"
        )

    def test_invalid_key_returns_401(self, inventory_api_base_url: str) -> None:
        """A request with a bogus API key must be rejected with 401 or 403."""
        client = _ProbeClient(inventory_api_base_url, "invalid-key-probe")
        with pytest.raises(requests.HTTPError) as exc_info:
            client.get("/health")
        assert exc_info.value.response.status_code in (401, 403), (
            "Expected 401/403 for invalid key, "
            f"got {exc_info.value.response.status_code}"
        )
