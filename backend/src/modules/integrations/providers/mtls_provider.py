"""mTLS outbound provider — client cert/key/CA stay server-side only."""

from __future__ import annotations

import asyncio
import contextlib
import os
import ssl
import tempfile
import time
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urljoin

import httpx

from src.modules.integrations.providers.base import (
    IntegrationSyncResult,
    IntegrationTestResult,
)
from src.modules.integrations.providers.rest_provider import (
    _extract_cursor,
    _extract_items,
    _safe_error,
    _safe_host,
)


class MTLSProvider:
    """ETAPA 4: mutual TLS with client certificate, private key, and optional CA."""

    type = "mtls"

    def __init__(
        self,
        *,
        max_retries: int = 3,
        retry_backoff_seconds: float = 0.4,
        max_pages: int = 20,
    ) -> None:
        self._max_retries = max_retries
        self._retry_backoff_seconds = retry_backoff_seconds
        self._max_pages = max_pages

    async def test_connection(
        self,
        *,
        configuration: dict[str, Any],
        secrets: dict[str, Any],
    ) -> IntegrationTestResult:
        base_url = _cfg(configuration, "base_url", "baseUrl")
        endpoint = _cfg(configuration, "endpoint") or "/"
        if not base_url:
            return IntegrationTestResult(
                success=False,
                message="Falha na conexão",
                error_detail="URL base não configurada.",
            )

        missing = _missing_mtls_secrets(secrets)
        if missing:
            return IntegrationTestResult(
                success=False,
                message="Falha na conexão",
                error_detail=(
                    "Certificado cliente ou chave privada não configurados no backend."
                ),
            )

        try:
            ssl_context = build_ssl_context(secrets)
        except _MTLSConfigError as exc:
            return IntegrationTestResult(
                success=False,
                message="Falha na conexão",
                server=_safe_host(base_url),
                authentication="mTLS",
                error_detail=str(exc),
            )

        started = time.perf_counter()
        try:
            response = await self._request(
                method="GET",
                url=_join(base_url, endpoint),
                configuration=configuration,
                ssl_context=ssl_context,
            )
        except httpx.TimeoutException:
            return IntegrationTestResult(
                success=False,
                message="Falha na conexão",
                server=_safe_host(base_url),
                authentication="mTLS",
                error_detail="Timeout ao contactar o servidor terceiro.",
            )
        except (httpx.HTTPError, ssl.SSLError) as exc:
            return IntegrationTestResult(
                success=False,
                message="Falha na conexão",
                server=_safe_host(base_url),
                authentication="mTLS",
                error_detail=_safe_tls_error(exc),
            )

        duration_ms = int((time.perf_counter() - started) * 1000)
        if response.status_code >= 400:
            return IntegrationTestResult(
                success=False,
                message="Falha na conexão",
                server=_safe_host(base_url),
                duration_ms=duration_ms,
                authentication="mTLS",
                error_detail=f"HTTP {response.status_code}",
            )

        return IntegrationTestResult(
            success=True,
            message="Conexão realizada com sucesso",
            server=_safe_host(base_url),
            duration_ms=duration_ms,
            authentication="mTLS",
            permission="mutual-tls",
        )

    async def sync(
        self,
        *,
        configuration: dict[str, Any],
        secrets: dict[str, Any],
    ) -> IntegrationSyncResult:
        started_at = datetime.now(UTC).isoformat()
        base_url = _cfg(configuration, "base_url", "baseUrl")
        endpoint = _cfg(configuration, "endpoint") or "/"
        if not base_url:
            finished = datetime.now(UTC).isoformat()
            return IntegrationSyncResult(
                success=False,
                mode="full",
                records_processed=0,
                message="URL base não configurada.",
                started_at=started_at,
                finished_at=finished,
            )
        if _missing_mtls_secrets(secrets):
            finished = datetime.now(UTC).isoformat()
            return IntegrationSyncResult(
                success=False,
                mode="full",
                records_processed=0,
                message="Certificado cliente ou chave privada não configurados.",
                started_at=started_at,
                finished_at=finished,
            )

        try:
            ssl_context = build_ssl_context(secrets)
        except _MTLSConfigError as exc:
            finished = datetime.now(UTC).isoformat()
            return IntegrationSyncResult(
                success=False,
                mode="full",
                records_processed=0,
                message=str(exc),
                started_at=started_at,
                finished_at=finished,
            )

        pagination = str(configuration.get("pagination") or "none").lower()
        rate_limit = configuration.get("rate_limit_per_minute") or configuration.get(
            "rateLimitPerMinute"
        )
        min_interval = 0.0
        if rate_limit is not None:
            try:
                rpm = float(rate_limit)
                if rpm > 0:
                    min_interval = 60.0 / rpm
            except (TypeError, ValueError):
                min_interval = 0.0

        records = 0
        page = 1
        offset = 0
        cursor: str | None = None
        url = _join(base_url, endpoint)

        try:
            for _ in range(self._max_pages):
                params: dict[str, Any] = {}
                if pagination == "offset":
                    params["limit"] = 100
                    params["offset"] = offset
                elif pagination == "page":
                    params["page"] = page
                    params["page_size"] = 100
                elif pagination == "cursor" and cursor:
                    params["cursor"] = cursor

                response = await self._request(
                    method="GET",
                    url=url,
                    configuration=configuration,
                    ssl_context=ssl_context,
                    params=params or None,
                )
                if response.status_code >= 400:
                    finished = datetime.now(UTC).isoformat()
                    return IntegrationSyncResult(
                        success=False,
                        mode="full" if pagination == "none" else "incremental",
                        records_processed=records,
                        message=f"HTTP {response.status_code} durante sync",
                        started_at=started_at,
                        finished_at=finished,
                    )

                batch = _extract_items(response)
                records += len(batch)

                if pagination == "none":
                    break
                if pagination == "offset":
                    if len(batch) < 100:
                        break
                    offset += len(batch)
                elif pagination == "page":
                    if len(batch) < 100:
                        break
                    page += 1
                elif pagination == "cursor":
                    next_cursor = _extract_cursor(response)
                    if not next_cursor or next_cursor == cursor:
                        break
                    cursor = next_cursor
                else:
                    break

                if min_interval > 0:
                    await asyncio.sleep(min_interval)
        except (httpx.HTTPError, ssl.SSLError) as exc:
            finished = datetime.now(UTC).isoformat()
            return IntegrationSyncResult(
                success=False,
                mode="full" if pagination == "none" else "incremental",
                records_processed=records,
                message=_safe_tls_error(exc),
                started_at=started_at,
                finished_at=finished,
            )

        finished = datetime.now(UTC).isoformat()
        return IntegrationSyncResult(
            success=True,
            mode="full" if pagination == "none" else "incremental",
            records_processed=records,
            message=f"Sync completed — {records} records",
            started_at=started_at,
            finished_at=finished,
        )

    async def _request(
        self,
        *,
        method: str,
        url: str,
        configuration: dict[str, Any],
        ssl_context: ssl.SSLContext,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:
        timeout_ms = configuration.get("timeout_ms") or configuration.get("timeoutMs") or 30_000
        try:
            timeout_s = max(float(timeout_ms) / 1000.0, 1.0)
        except (TypeError, ValueError):
            timeout_s = 30.0

        headers = {"Accept": "application/json"}
        raw_headers = configuration.get("headers")
        if isinstance(raw_headers, dict):
            for key, value in raw_headers.items():
                if value is not None:
                    headers[str(key)] = str(value)

        last_exc: Exception | None = None
        async with httpx.AsyncClient(
            timeout=timeout_s,
            follow_redirects=True,
            verify=ssl_context,
        ) as client:
            for attempt in range(self._max_retries + 1):
                try:
                    response = await client.request(
                        method, url, headers=headers, params=params
                    )
                    retryable = response.status_code in {429, 500, 502, 503, 504}
                    if retryable and attempt < self._max_retries:
                        await asyncio.sleep(self._retry_backoff_seconds * (2**attempt))
                        continue
                    return response
                except (httpx.TimeoutException, httpx.TransportError, ssl.SSLError) as exc:
                    last_exc = exc
                    if attempt >= self._max_retries:
                        raise
                    await asyncio.sleep(self._retry_backoff_seconds * (2**attempt))

        assert last_exc is not None
        raise last_exc


class _MTLSConfigError(Exception):
    """Safe mTLS material error (never includes PEM contents)."""


def build_ssl_context(secrets: dict[str, Any]) -> ssl.SSLContext:
    """Build an SSLContext from PEM secrets. Raises _MTLSConfigError on bad material."""
    client_cert = _secret(
        secrets, "client_cert_pem", "client_certificate", "clientCertPem"
    )
    client_key = _secret(
        secrets, "client_key_pem", "private_key", "clientKeyPem", "privateKey"
    )
    ca_cert = _secret(secrets, "ca_cert_pem", "ca_certificate", "caCertPem", "ca")

    if not client_cert or not client_key:
        raise _MTLSConfigError(
            "Certificado cliente e chave privada são obrigatórios."
        )
    if "BEGIN CERTIFICATE" not in client_cert:
        raise _MTLSConfigError("Certificado cliente PEM inválido.")
    if "BEGIN" not in client_key or "PRIVATE KEY" not in client_key:
        raise _MTLSConfigError("Chave privada PEM inválida.")

    ctx = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH)
    if ca_cert:
        if "BEGIN CERTIFICATE" not in ca_cert:
            raise _MTLSConfigError("CA certificate PEM inválido.")
        try:
            ctx.load_verify_locations(cadata=ca_cert)
        except ssl.SSLError as exc:
            raise _MTLSConfigError("Não foi possível carregar o CA certificate.") from exc
    else:
        # Still verify against system trust store when CA not provided.
        ctx.check_hostname = True
        ctx.verify_mode = ssl.CERT_REQUIRED

    cert_path = ""
    key_path = ""
    try:
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".crt") as cert_file:
            cert_file.write(client_cert)
            if not client_cert.endswith("\n"):
                cert_file.write("\n")
            cert_path = cert_file.name
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".key") as key_file:
            key_file.write(client_key)
            if not client_key.endswith("\n"):
                key_file.write("\n")
            key_path = key_file.name
        try:
            ctx.load_cert_chain(certfile=cert_path, keyfile=key_path)
        except ssl.SSLError as exc:
            raise _MTLSConfigError(
                "Não foi possível carregar o certificado/chave do cliente."
            ) from exc
    finally:
        for path in (cert_path, key_path):
            if path and os.path.exists(path):
                with contextlib.suppress(OSError):
                    os.unlink(path)

    return ctx


def _missing_mtls_secrets(secrets: dict[str, Any]) -> bool:
    client_cert = _secret(
        secrets, "client_cert_pem", "client_certificate", "clientCertPem"
    )
    client_key = _secret(
        secrets, "client_key_pem", "private_key", "clientKeyPem", "privateKey"
    )
    return not client_cert or not client_key


def _cfg(configuration: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = configuration.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _secret(secrets: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = secrets.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _join(base_url: str, endpoint: str) -> str:
    if endpoint.startswith("http://") or endpoint.startswith("https://"):
        return endpoint
    return urljoin(base_url.rstrip("/") + "/", endpoint.lstrip("/"))


def _safe_tls_error(exc: Exception) -> str:
    text = _safe_error(exc)
    lowered = text.lower()
    for needle in ("private key", "certificate", "-----begin", "pem"):
        if needle in lowered:
            return "Falha TLS/mTLS ao contactar o servidor terceiro."
    return text
