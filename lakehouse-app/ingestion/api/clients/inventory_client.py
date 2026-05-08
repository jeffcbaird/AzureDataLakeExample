"""Inventory API ingestion client.

Fetches daily inventory snapshots from the source API.

Expected Key Vault secret: ``inventory-api-key``
Expected env var (optional override): ``INVENTORY_API_BASE_URL``
"""
from __future__ import annotations

import os

from lakehouse_common.clients.base_http import ApiKeyAuth, BaseHttpClient


class InventoryClient(BaseHttpClient):
    BASE_URL = os.environ.get(
        "INVENTORY_API_BASE_URL", "https://api.example-inventory.com/v2"
    )

    def __init__(self, api_key: str) -> None:
        super().__init__(auth=ApiKeyAuth("X-Api-Key", api_key))

    def list_snapshots(self, date: str, page_size: int = 500) -> list[dict]:
        """Return all inventory snapshots as-of *date* (``YYYY-MM-DD``)."""
        return list(
            self.paginate(
                "/snapshots",
                params={"as_of_date": date, "page_size": page_size},
                results_key="snapshots",
            )
        )
