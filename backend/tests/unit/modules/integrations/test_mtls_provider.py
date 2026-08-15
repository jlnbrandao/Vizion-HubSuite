"""Unit tests for MTLSProvider."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx
import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from src.modules.integrations.providers.mtls_provider import (
    MTLSProvider,
    _MTLSConfigError,
    build_ssl_context,
)


def _pem_bundle() -> tuple[str, str, str]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name(
        [x509.NameAttribute(NameOID.COMMON_NAME, "vizion-mtls-test")]
    )
    now = datetime.now(UTC)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=1))
        .sign(key, hashes.SHA256())
    )
    cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode()
    key_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    return cert_pem, key_pem, cert_pem  # self-signed CA == cert


def _patch_client(monkeypatch: pytest.MonkeyPatch, handler) -> None:  # type: ignore[no-untyped-def]
    transport = httpx.MockTransport(handler)
    real_client = httpx.AsyncClient

    def factory(*args, **kwargs):  # type: ignore[no-untyped-def]
        kwargs["transport"] = transport
        kwargs.setdefault("follow_redirects", True)
        return real_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", factory)


def test_build_ssl_context_loads_pems() -> None:
    cert, key, ca = _pem_bundle()
    ctx = build_ssl_context(
        {
            "client_cert_pem": cert,
            "client_key_pem": key,
            "ca_cert_pem": ca,
        }
    )
    assert ctx is not None


def test_build_ssl_context_rejects_invalid_cert() -> None:
    _, key, _ = _pem_bundle()
    with pytest.raises(_MTLSConfigError, match="Certificado cliente PEM inválido"):
        build_ssl_context({"client_cert_pem": "not-a-pem", "client_key_pem": key})


@pytest.mark.asyncio
async def test_mtls_missing_secrets() -> None:
    provider = MTLSProvider()
    result = await provider.test_connection(
        configuration={"base_url": "https://api.example.com", "endpoint": "/"},
        secrets={},
    )
    assert result.success is False
    assert "certificado" in (result.error_detail or "").lower()


@pytest.mark.asyncio
async def test_mtls_test_connection_success(monkeypatch: pytest.MonkeyPatch) -> None:
    cert, key, ca = _pem_bundle()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/secure"
        return httpx.Response(200, json={"ok": True})

    _patch_client(monkeypatch, handler)
    provider = MTLSProvider(max_retries=0)
    result = await provider.test_connection(
        configuration={
            "base_url": "https://api.example.com",
            "endpoint": "/secure",
            "timeout_ms": 5000,
        },
        secrets={
            "client_cert_pem": cert,
            "client_key_pem": key,
            "ca_cert_pem": ca,
        },
    )
    assert result.success is True
    assert result.authentication == "mTLS"
    assert result.permission == "mutual-tls"
    assert "BEGIN CERTIFICATE" not in (result.message or "")
    assert "PRIVATE KEY" not in (result.error_detail or "")


@pytest.mark.asyncio
async def test_mtls_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    cert, key, ca = _pem_bundle()
    _patch_client(
        monkeypatch,
        lambda _r: httpx.Response(403, json={"error": "forbidden"}),
    )
    provider = MTLSProvider(max_retries=0)
    result = await provider.test_connection(
        configuration={"base_url": "https://api.example.com", "endpoint": "/"},
        secrets={
            "client_cert_pem": cert,
            "client_key_pem": key,
            "ca_cert_pem": ca,
        },
    )
    assert result.success is False
    assert result.error_detail == "HTTP 403"
