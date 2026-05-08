"""Bronze container writer for the ingestion Function App.

Serialises records as NDJSON and uploads to::

    bronze/<source>/<YYYY-MM-DD>/data.ndjson

Uses DefaultAzureCredential (managed identity in Azure, ``az login`` locally).
The Function App MI must hold Storage Blob Data Contributor on the bronze
container — granted via rbac.tf when deploy_expensive_resources = true.
"""
from __future__ import annotations

import json

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

from .keyvault import get_secret


def _blob_client() -> BlobServiceClient:
    # The DFS endpoint stored in KV; swap to blob endpoint for SDK compatibility.
    dfs_endpoint = get_secret("adls-primary-dfs-endpoint").rstrip("/")
    blob_endpoint = dfs_endpoint.replace(".dfs.core.windows.net", ".blob.core.windows.net")
    return BlobServiceClient(account_url=blob_endpoint, credential=DefaultAzureCredential())


def write_bronze(source: str, date: str, records: list[dict]) -> int:
    """Upload *records* as NDJSON to ``bronze/<source>/<date>/data.ndjson``.

    Returns the number of records written.
    """
    ndjson_bytes = "\n".join(json.dumps(r) for r in records).encode()
    blob = _blob_client().get_blob_client(
        container="bronze",
        blob=f"{source}/{date}/data.ndjson",
    )
    blob.upload_blob(ndjson_bytes, overwrite=True)
    return len(records)
