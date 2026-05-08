"""Sales API ingestion client.

Fetches daily order records from the source API and returns them as a list
of dicts ready to be serialised as NDJSON into the bronze container.

Expected Key Vault secret: ``sales-api-key``
Expected env var (optional override): ``SALES_API_BASE_URL``
"""
from __future__ import annotations

import os

from lakehouse_common.clients.base_http import ApiKeyAuth, BaseHttpClient


class SalesClient(BaseHttpClient):
    BASE_URL = os.environ.get(
        "SALES_API_BASE_URL", "https://api.example-sales.com/v1"
    )

    def __init__(self, api_key: str) -> None:
        super().__init__(auth=ApiKeyAuth("X-Api-Key", api_key))

    def list_orders(self, date: str, page_size: int = 200) -> list[dict]:
        """Return all orders for *date* (``YYYY-MM-DD``).

        Pages through the ``/orders`` endpoint following ``next_url``
        envelope keys until exhausted.
        """
        return list(
            self.paginate(
                "/orders",
                params={"date": date, "limit": page_size},
                results_key="orders",
            )
        )
