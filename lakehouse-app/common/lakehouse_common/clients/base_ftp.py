"""Base FTP / SFTP client.

Supports plain FTP (via :mod:`ftplib`) and SFTP (via :mod:`paramiko`).
Uses a context-manager protocol so connections are always closed cleanly.

Typical usage — SFTP::

    with BaseFtpClient.sftp(
        host="files.example.com",
        username=get_secret("ftp-user"),
        password=get_secret("ftp-pass"),
    ) as client:
        files = client.list_dir("/inbox")
        for name in files:
            data = client.download(f"/inbox/{name}")
            upload_to_bronze(data, name)

Typical usage — FTP::

    with BaseFtpClient.ftp(
        host="legacy.example.com",
        username=get_secret("ftp-user"),
        password=get_secret("ftp-pass"),
    ) as client:
        files = client.list_dir("/export")
"""
from __future__ import annotations

import ftplib
import io
import logging
from typing import IO

import paramiko

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class FtpConnectionError(RuntimeError):
    """Raised when the client cannot establish or maintain a connection."""


class FtpTransferError(RuntimeError):
    """Raised when a file download or upload fails."""


# ---------------------------------------------------------------------------
# Base class — shared interface
# ---------------------------------------------------------------------------

class BaseFtpClient:
    """Abstract base: subclass or use the factory classmethods."""

    def list_dir(self, remote_path: str) -> list[str]:  # pragma: no cover
        raise NotImplementedError

    def download(self, remote_path: str) -> bytes:  # pragma: no cover
        raise NotImplementedError

    def upload(self, remote_path: str, data: bytes) -> None:  # pragma: no cover
        raise NotImplementedError

    def close(self) -> None:  # pragma: no cover
        raise NotImplementedError

    def __enter__(self) -> "BaseFtpClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Factory classmethods
    # ------------------------------------------------------------------

    @classmethod
    def sftp(
        cls,
        host: str,
        username: str,
        password: str | None = None,
        private_key: paramiko.PKey | None = None,
        port: int = 22,
        timeout: int = 30,
    ) -> "SftpClient":
        """Return a connected :class:`SftpClient`."""
        return SftpClient(
            host=host,
            username=username,
            password=password,
            private_key=private_key,
            port=port,
            timeout=timeout,
        )

    @classmethod
    def ftp(
        cls,
        host: str,
        username: str,
        password: str,
        port: int = 21,
        timeout: int = 30,
        use_passive: bool = True,
    ) -> "PlainFtpClient":
        """Return a connected :class:`PlainFtpClient`."""
        return PlainFtpClient(
            host=host,
            username=username,
            password=password,
            port=port,
            timeout=timeout,
            use_passive=use_passive,
        )


# ---------------------------------------------------------------------------
# SFTP implementation (paramiko)
# ---------------------------------------------------------------------------

class SftpClient(BaseFtpClient):
    """SFTP client backed by paramiko.  Supports password or private-key auth."""

    def __init__(
        self,
        host: str,
        username: str,
        password: str | None,
        private_key: paramiko.PKey | None,
        port: int,
        timeout: int,
    ) -> None:
        self._transport: paramiko.Transport | None = None
        self._sftp: paramiko.SFTPClient | None = None

        try:
            self._transport = paramiko.Transport((host, port))
            self._transport.connect(
                username=username,
                password=password,
                pkey=private_key,
            )
            self._sftp = paramiko.SFTPClient.from_transport(self._transport)
            logger.info("SFTP connected: %s@%s:%d", username, host, port)
        except paramiko.AuthenticationException as exc:
            raise FtpConnectionError(f"SFTP auth failed for {username}@{host}") from exc
        except Exception as exc:
            raise FtpConnectionError(f"SFTP connection failed to {host}:{port}") from exc

    def list_dir(self, remote_path: str) -> list[str]:
        """Return filenames (not full paths) in *remote_path*."""
        assert self._sftp is not None
        try:
            return self._sftp.listdir(remote_path)
        except IOError as exc:
            raise FtpTransferError(f"Cannot list {remote_path}") from exc

    def download(self, remote_path: str) -> bytes:
        """Download *remote_path* and return its contents as bytes."""
        assert self._sftp is not None
        buf = io.BytesIO()
        try:
            self._sftp.getfo(remote_path, buf)
        except IOError as exc:
            raise FtpTransferError(f"Download failed: {remote_path}") from exc
        logger.debug("Downloaded %s (%d bytes)", remote_path, buf.tell())
        return buf.getvalue()

    def upload(self, remote_path: str, data: bytes) -> None:
        """Upload *data* to *remote_path*, creating parent dirs if needed."""
        assert self._sftp is not None
        buf = io.BytesIO(data)
        try:
            self._sftp.putfo(buf, remote_path)
        except IOError as exc:
            raise FtpTransferError(f"Upload failed: {remote_path}") from exc
        logger.debug("Uploaded %s (%d bytes)", remote_path, len(data))

    def close(self) -> None:
        if self._sftp:
            self._sftp.close()
        if self._transport:
            self._transport.close()


# ---------------------------------------------------------------------------
# Plain FTP implementation (ftplib)
# ---------------------------------------------------------------------------

class PlainFtpClient(BaseFtpClient):
    """Plain FTP client backed by :mod:`ftplib`."""

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        port: int,
        timeout: int,
        use_passive: bool,
    ) -> None:
        try:
            self._ftp = ftplib.FTP(timeout=timeout)
            self._ftp.connect(host, port)
            self._ftp.login(username, password)
            self._ftp.set_pasv(use_passive)
            logger.info("FTP connected: %s@%s:%d", username, host, port)
        except ftplib.Error as exc:
            raise FtpConnectionError(f"FTP connection failed to {host}:{port}") from exc

    def list_dir(self, remote_path: str) -> list[str]:
        """Return filenames in *remote_path*."""
        try:
            return self._ftp.nlst(remote_path)
        except ftplib.Error as exc:
            raise FtpTransferError(f"Cannot list {remote_path}") from exc

    def download(self, remote_path: str) -> bytes:
        """Download *remote_path* and return its contents as bytes."""
        buf = io.BytesIO()
        try:
            self._ftp.retrbinary(f"RETR {remote_path}", buf.write)
        except ftplib.Error as exc:
            raise FtpTransferError(f"Download failed: {remote_path}") from exc
        logger.debug("Downloaded %s (%d bytes)", remote_path, buf.tell())
        return buf.getvalue()

    def upload(self, remote_path: str, data: bytes) -> None:
        """Upload *data* to *remote_path*."""
        buf = io.BytesIO(data)
        try:
            self._ftp.storbinary(f"STOR {remote_path}", buf)
        except ftplib.Error as exc:
            raise FtpTransferError(f"Upload failed: {remote_path}") from exc
        logger.debug("Uploaded %s (%d bytes)", remote_path, len(data))

    def close(self) -> None:
        try:
            self._ftp.quit()
        except Exception:
            self._ftp.close()
