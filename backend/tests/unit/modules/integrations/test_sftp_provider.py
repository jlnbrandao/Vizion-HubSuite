"""Unit tests for SFTPProvider (paramiko SSHClient mocked)."""

from __future__ import annotations

from io import BytesIO
from typing import Any
from unittest.mock import MagicMock

import paramiko
import pytest

from src.modules.integrations.providers.sftp_provider import SFTPProvider


class _FakeSFTP:
    def __init__(self, files: dict[str, bytes]) -> None:
        self._files = files

    def listdir(self, path: str) -> list[str]:  # noqa: ARG002
        return list(self._files)

    def open(self, path: str, mode: str = "r") -> BytesIO:  # noqa: ARG002
        name = path.rsplit("/", 1)[-1]
        return BytesIO(self._files[name])

    def close(self) -> None:
        return None


@pytest.fixture
def patch_sftp(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    state: dict[str, Any] = {"files": {}, "connect_kwargs": None}

    class FakeClient:
        def set_missing_host_key_policy(self, _policy: Any) -> None:
            return None

        def connect(self, **kwargs: Any) -> None:
            state["connect_kwargs"] = kwargs

        def open_sftp(self) -> _FakeSFTP:
            return _FakeSFTP(state["files"])

        def close(self) -> None:
            return None

    monkeypatch.setattr(paramiko, "SSHClient", FakeClient)
    monkeypatch.setattr(
        paramiko.RSAKey,
        "from_private_key",
        staticmethod(lambda _file_obj, password=None: MagicMock(password=password)),
    )
    return state


_PEM = (
    "-----BEGIN RSA PRIVATE KEY-----\n"
    "abc\n"
    "-----END RSA PRIVATE KEY-----"
)


@pytest.mark.asyncio
async def test_sftp_test_connection_success(patch_sftp: dict[str, Any]) -> None:
    patch_sftp["files"] = {"a.csv": b"id,name\n1,x\n", "b.txt": b"x"}
    provider = SFTPProvider()
    result = await provider.test_connection(
        configuration={
            "host": "sftp.example.com",
            "port": 22,
            "username": "svc",
            "auth_type": "private_key",
            "remote_path": "/inbox",
            "schedule_cron": "0 */6 * * *",
        },
        secrets={"private_key_pem": _PEM},
    )
    assert result.success is True
    assert result.server == "sftp.example.com:22"
    assert result.authentication == "SFTP private key"
    assert "schedule=0 */6 * * *" in (result.permission or "")
    assert patch_sftp["connect_kwargs"]["username"] == "svc"
    assert "password" not in (patch_sftp["connect_kwargs"] or {})


@pytest.mark.asyncio
async def test_sftp_missing_secret() -> None:
    provider = SFTPProvider()
    result = await provider.test_connection(
        configuration={
            "host": "sftp.example.com",
            "username": "svc",
            "auth_type": "password",
            "remote_path": "/",
        },
        secrets={},
    )
    assert result.success is False
    assert "senha" in (result.error_detail or "").lower()


@pytest.mark.asyncio
async def test_sftp_sync_parses_csv(patch_sftp: dict[str, Any]) -> None:
    patch_sftp["files"] = {
        "addresses_2026.csv": b"id,city\n1,SP\n2,RJ\n",
        "readme.txt": b"ignore",
        "addresses_old.csv": b"id,city\n3,BH\n",
    }
    provider = SFTPProvider()
    result = await provider.sync(
        configuration={
            "host": "sftp.example.com",
            "username": "svc",
            "auth_type": "password",
            "remote_path": "/data",
            "filename_pattern": "addresses_*.csv",
            "encoding": "utf-8",
            "delimiter": ",",
            "schedule_cron": "0 2 * * *",
        },
        secrets={"password": "s3cret"},
    )
    assert result.success is True
    assert result.records_processed == 3  # 2 + 1 data rows
    assert "2 arquivo(s)" in result.message
    assert patch_sftp["connect_kwargs"]["password"] == "s3cret"
    assert "s3cret" not in result.message


@pytest.mark.asyncio
async def test_sftp_sync_bad_encoding(patch_sftp: dict[str, Any]) -> None:
    patch_sftp["files"] = {"a.csv": "ação".encode("latin-1")}
    provider = SFTPProvider()
    result = await provider.sync(
        configuration={
            "host": "sftp.example.com",
            "username": "svc",
            "auth_type": "password",
            "remote_path": "/",
            "filename_pattern": "*.csv",
            "encoding": "utf-8",
        },
        secrets={"password": "x"},
    )
    assert result.success is False
    assert "encoding" in result.message.lower()
