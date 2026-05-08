"""FTP ingestion Blueprint.

Each function runs on a daily timer, downloads files from an FTP/SFTP inbox,
and writes them to the bronze container preserving the original filename.

Bronze layout: ``bronze/<source>/<YYYY-MM-DD>/<original_filename>``

Key Vault secrets consumed:
    ftp-<source>-host      — FTP hostname
    ftp-<source>-username  — FTP username
    ftp-<source>-password  — FTP password
    adls-primary-dfs-endpoint — ADLS DFS endpoint URL

Set ``FTP_<SOURCE>_USE_SFTP=true`` to use SFTP instead of plain FTP.
"""
from __future__ import annotations

import datetime

import os

import azure.functions as func
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

from lakehouse_common.clients.base_ftp import BaseFtpClient

from shared.keyvault import get_secret
from shared.logging import get_logger

bp = func.Blueprint()
# ── Shared FTP→bronze helper ───────────────────────────────────────────────────

def _ingest_ftp_source(source: str, remote_dir: str, use_sftp: bool = False) -> None:
    """Download all files in *remote_dir* and upload them to bronze."""
    log = get_logger(source)
    date = datetime.date.today().isoformat()
    log.info("ftp.ingestion.start", date=date, remote_dir=remote_dir)

    host = get_secret(f"ftp-{source}-host")
    username = get_secret(f"ftp-{source}-username")
    password = get_secret(f"ftp-{source}-password")

    dfs_endpoint = get_secret("adls-primary-dfs-endpoint").rstrip("/")
    blob_endpoint = dfs_endpoint.replace(".dfs.core.windows.net", ".blob.core.windows.net")
    blob_svc = BlobServiceClient(account_url=blob_endpoint, credential=DefaultAzureCredential())

    factory = BaseFtpClient.sftp if use_sftp else BaseFtpClient.ftp
    with factory(host=host, username=username, password=password) as ftp:
        files = ftp.list_dir(remote_dir)
        for filename in files:
            data = ftp.download(f"{remote_dir}/{filename}")
            blob = blob_svc.get_blob_client(
                container="bronze",
                blob=f"{source}/{date}/{filename}",
            )
            blob.upload_blob(data, overwrite=True)
            log.info("ftp.file.uploaded", filename=filename)

    log.info("ftp.ingestion.complete", date=date, file_count=len(files))
# ── Partner drops (example SFTP source) ──────────────────────────────────────

@bp.timer_trigger(
    schedule="0 0 3 * * *",  # 03:00 UTC daily
    arg_name="timer",
    run_on_startup=False,
    use_monitor=True,
)
def ingest_partner_drops(timer: func.TimerRequest) -> None:
    use_sftp = os.environ.get("FTP_PARTNER_USE_SFTP", "true").lower() == "true"
    _ingest_ftp_source(
        source="partner-drops",
        remote_dir="/outbox",
        use_sftp=use_sftp,
    )
