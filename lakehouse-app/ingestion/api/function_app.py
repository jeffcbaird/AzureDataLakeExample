"""API ingestion Blueprint.

Each function runs on a daily timer, fetches records from one REST API,
and writes NDJSON to the bronze container.

Bronze layout: ``bronze/<source>/<YYYY-MM-DD>/data.ndjson``

Key Vault secrets consumed:
    sales-api-key        — API key for the Sales source
    inventory-api-key    — API key for the Inventory source
    adls-primary-dfs-endpoint — ADLS DFS endpoint URL
"""
from __future__ import annotations

import datetime

import azure.functions as func

from shared.bronze import write_bronze
from shared.keyvault import get_secret
from shared.logging import get_logger

from .clients.inventory_client import InventoryClient
from .clients.sales_client import SalesClient

bp = func.Blueprint()


# ── Sales ──────────────────────────────────────────────────────────────────────

@bp.timer_trigger(
    schedule="0 0 2 * * *",  # 02:00 UTC daily
    arg_name="timer",
    run_on_startup=False,
    use_monitor=True,
)
def ingest_sales(timer: func.TimerRequest) -> None:
    log = get_logger("sales")
    date = datetime.date.today().isoformat()
    log.info("ingestion.start", date=date)

    records = SalesClient(get_secret("sales-api-key")).list_orders(date)
    count = write_bronze("sales", date, records)

    log.info("ingestion.complete", date=date, record_count=count)


# ── Inventory ─────────────────────────────────────────────────────────────────

@bp.timer_trigger(
    schedule="0 30 2 * * *",  # 02:30 UTC daily
    arg_name="timer",
    run_on_startup=False,
    use_monitor=True,
)
def ingest_inventory(timer: func.TimerRequest) -> None:
    log = get_logger("inventory")
    date = datetime.date.today().isoformat()
    log.info("ingestion.start", date=date)

    records = InventoryClient(get_secret("inventory-api-key")).list_snapshots(date)
    count = write_bronze("inventory", date, records)

    log.info("ingestion.complete", date=date, record_count=count)
