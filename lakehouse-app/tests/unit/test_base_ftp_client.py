"""Unit tests for BaseFtpClient — SFTP and plain FTP, with mocked transports."""
from __future__ import annotations

import io
import ftplib
from unittest.mock import MagicMock, patch, call

import pytest
import paramiko

from lakehouse_common.clients.base_ftp import (
    BaseFtpClient,
    FtpConnectionError,
    FtpTransferError,
    PlainFtpClient,
    SftpClient,
)


# ---------------------------------------------------------------------------
# SFTP tests
# ---------------------------------------------------------------------------

class TestSftpClient:

    @pytest.fixture()
    def mock_transport_and_sftp(self):
        """Patch paramiko.Transport and SFTPClient.from_transport."""
        mock_transport = MagicMock(spec=paramiko.Transport)
        mock_sftp = MagicMock(spec=paramiko.SFTPClient)

        with patch("paramiko.Transport", return_value=mock_transport), \
             patch("paramiko.SFTPClient.from_transport", return_value=mock_sftp):
            yield mock_transport, mock_sftp

    def test_list_dir_returns_filenames(self, mock_transport_and_sftp):
        _, mock_sftp = mock_transport_and_sftp
        mock_sftp.listdir.return_value = ["file1.csv", "file2.csv"]

        client = BaseFtpClient.sftp("host", "user", "pass")
        result = client.list_dir("/inbox")

        assert result == ["file1.csv", "file2.csv"]
        mock_sftp.listdir.assert_called_once_with("/inbox")

    def test_download_returns_bytes(self, mock_transport_and_sftp):
        _, mock_sftp = mock_transport_and_sftp
        payload = b"col1,col2\n1,2\n"

        def fake_getfo(path, buf):
            buf.write(payload)

        mock_sftp.getfo.side_effect = fake_getfo
        client = BaseFtpClient.sftp("host", "user", "pass")
        result = client.download("/inbox/data.csv")

        assert result == payload

    def test_upload_sends_bytes(self, mock_transport_and_sftp):
        _, mock_sftp = mock_transport_and_sftp
        client = BaseFtpClient.sftp("host", "user", "pass")
        client.upload("/outbox/result.csv", b"a,b\n1,2\n")

        mock_sftp.putfo.assert_called_once()
        buf_arg = mock_sftp.putfo.call_args[0][0]
        assert buf_arg.getvalue() == b"a,b\n1,2\n"

    def test_close_closes_sftp_and_transport(self, mock_transport_and_sftp):
        mock_transport, mock_sftp = mock_transport_and_sftp
        client = BaseFtpClient.sftp("host", "user", "pass")
        client.close()

        mock_sftp.close.assert_called_once()
        mock_transport.close.assert_called_once()

    def test_context_manager_closes_on_exit(self, mock_transport_and_sftp):
        mock_transport, mock_sftp = mock_transport_and_sftp
        with BaseFtpClient.sftp("host", "user", "pass"):
            pass
        mock_sftp.close.assert_called_once()

    def test_auth_failure_raises_ftp_connection_error(self):
        mock_transport = MagicMock()
        mock_transport.connect.side_effect = paramiko.AuthenticationException("denied")

        with patch("paramiko.Transport", return_value=mock_transport):
            with pytest.raises(FtpConnectionError, match="auth failed"):
                BaseFtpClient.sftp("host", "user", "wrong-pass")

    def test_list_dir_io_error_raises_transfer_error(self, mock_transport_and_sftp):
        _, mock_sftp = mock_transport_and_sftp
        mock_sftp.listdir.side_effect = IOError("not found")

        client = BaseFtpClient.sftp("host", "user", "pass")
        with pytest.raises(FtpTransferError):
            client.list_dir("/no-such-dir")


# ---------------------------------------------------------------------------
# Plain FTP tests
# ---------------------------------------------------------------------------

class TestPlainFtpClient:

    @pytest.fixture()
    def mock_ftp(self):
        """Patch ftplib.FTP with a mock."""
        mock = MagicMock(spec=ftplib.FTP)
        with patch("ftplib.FTP", return_value=mock):
            yield mock

    def test_list_dir_returns_filenames(self, mock_ftp):
        mock_ftp.nlst.return_value = ["/export/file1.csv", "/export/file2.csv"]

        client = BaseFtpClient.ftp("host", "user", "pass")
        result = client.list_dir("/export")

        assert result == ["/export/file1.csv", "/export/file2.csv"]
        mock_ftp.nlst.assert_called_once_with("/export")

    def test_download_returns_bytes(self, mock_ftp):
        payload = b"data"

        def fake_retrbinary(cmd, callback):
            callback(payload)

        mock_ftp.retrbinary.side_effect = fake_retrbinary
        client = BaseFtpClient.ftp("host", "user", "pass")
        result = client.download("/export/data.csv")

        assert result == payload

    def test_upload_calls_storbinary(self, mock_ftp):
        client = BaseFtpClient.ftp("host", "user", "pass")
        client.upload("/inbox/out.csv", b"x,y\n")

        mock_ftp.storbinary.assert_called_once()
        cmd = mock_ftp.storbinary.call_args[0][0]
        assert cmd == "STOR /inbox/out.csv"

    def test_close_calls_quit(self, mock_ftp):
        client = BaseFtpClient.ftp("host", "user", "pass")
        client.close()
        mock_ftp.quit.assert_called_once()

    def test_close_falls_back_to_close_on_quit_error(self, mock_ftp):
        mock_ftp.quit.side_effect = ftplib.Error("already closed")
        client = BaseFtpClient.ftp("host", "user", "pass")
        client.close()
        mock_ftp.close.assert_called_once()

    def test_connection_error_raises_ftp_connection_error(self):
        mock_ftp_instance = MagicMock(spec=ftplib.FTP)
        mock_ftp_instance.connect.side_effect = ftplib.Error("refused")

        with patch("ftplib.FTP", return_value=mock_ftp_instance):
            with pytest.raises(FtpConnectionError):
                BaseFtpClient.ftp("host", "user", "pass")

    def test_download_error_raises_transfer_error(self, mock_ftp):
        mock_ftp.retrbinary.side_effect = ftplib.Error("transfer aborted")
        client = BaseFtpClient.ftp("host", "user", "pass")
        with pytest.raises(FtpTransferError):
            client.download("/export/broken.csv")
