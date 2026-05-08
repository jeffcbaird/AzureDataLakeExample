"""Integration tests — FTP/SFTP source health checks.

Each test connects to a source FTP host using the same credentials used in
production (Key Vault → host/username/password) and lists the inbox directory.
A successful directory listing confirms:
  - DNS resolution works for the host
  - TCP port is reachable
  - Credentials are valid
  - The expected inbox directory exists

A test failure means either the FTP host is unreachable or credentials have
been rotated without updating Key Vault.
"""
from __future__ import annotations

import os

import pytest

from lakehouse_common.clients.base_ftp import BaseFtpClient, FtpConnectionError

pytestmark = pytest.mark.integration

# Default inbox path — override via env var for non-standard source layouts.
_PARTNER_INBOX = os.environ.get("FTP_PARTNER_DROPS_INBOX", "/outbox")
_USE_SFTP = os.environ.get("FTP_PARTNER_USE_SFTP", "true").lower() == "true"


class TestPartnerDropsFtpHealth:
    def test_can_connect_and_list_inbox(self, partner_ftp_creds: dict) -> None:
        """Connect to the partner SFTP/FTP host and list the inbox directory."""
        factory = BaseFtpClient.sftp if _USE_SFTP else BaseFtpClient.ftp
        with factory(**partner_ftp_creds) as client:
            files = client.list_dir(_PARTNER_INBOX)
        # An empty inbox is fine — the important thing is the connection succeeded.
        assert isinstance(files, list), (
            f"list_dir returned {type(files)}, expected list"
        )

    def test_bad_password_raises_connection_error(
        self, partner_ftp_creds: dict
    ) -> None:
        """A wrong password must raise FtpConnectionError, not hang or crash."""
        bad_creds = {**partner_ftp_creds, "password": "wrong-password-probe"}
        factory = BaseFtpClient.sftp if _USE_SFTP else BaseFtpClient.ftp
        with pytest.raises(FtpConnectionError):
            with factory(**bad_creds) as client:
                client.list_dir(_PARTNER_INBOX)

    def test_inbox_path_exists(self, partner_ftp_creds: dict) -> None:
        """The configured inbox path must be listable (not raise on missing dir)."""
        factory = BaseFtpClient.sftp if _USE_SFTP else BaseFtpClient.ftp
        with factory(**partner_ftp_creds) as client:
            try:
                client.list_dir(_PARTNER_INBOX)
            except Exception as exc:
                pytest.fail(
                    f"Inbox path '{_PARTNER_INBOX}' is not accessible: {exc}"
                )
