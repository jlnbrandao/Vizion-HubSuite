"""HTTPS file provider — download JSON/CSV server-side (httpx)."""

from __future__ import annotations

import csv
import io
import json
import time
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

import httpx

from src.modules.integrations.providers.base import (
    IntegrationSyncResult,
    IntegrationTestResult,
)
from src.modules.integrations.providers.rest_provider import (
    _auth_label,
    _build_headers,
    _safe_error,
    _safe_host,
)


class HttpFileProvider:
    """ETAPA 7: pull a remote JSON/CSV file over HTTPS with optional auth."""

    type = "http_file"

    def __init__(
        self,
        *,
        max_retries: int = 3,
        retry_backoff_seconds: float = 0.4,
        max_bytes: int = 10 * 1024 * 1024,
    ) -> None:
        self._max_retries = max_retries
        self._retry_backoff_seconds = retry_backoff_seconds
        self._max_bytes = max_bytes

    async def test_connection(
        self,
        *,
        configuration: dict[str, Any],
        secrets: dict[str, Any],
    ) -> IntegrationTestResult:
        url = _url(configuration)
        if not url:
            return IntegrationTestResult(
                success=False,
                message="Falha na conexão",
                error_detail="URL do arquivo não configurada.",
            )
        if err := _url_scheme_error(url):
            return IntegrationTestResult(
                success=False,
                message="Falha na conexão",
                error_detail=err,
            )
        if err := _missing_auth_secret(configuration, secrets):
            return IntegrationTestResult(
                success=False,
                message="Falha na conexão",
                error_detail=err,
            )

        fmt = _format(configuration)
        auth_label = _auth_label(configuration)
        started = time.perf_counter()
        try:
            response = await self._download(
                url=url, configuration=configuration, secrets=secrets, method="HEAD"
            )
            # Some servers reject HEAD — fall back to GET with limited body.
            if response.status_code in {405, 501}:
                response = await self._download(
                    url=url, configuration=configuration, secrets=secrets, method="GET"
                )
        except httpx.TimeoutException:
            return IntegrationTestResult(
                success=False,
                message="Falha na conexão",
                server=_safe_host(url),
                authentication=auth_label,
                error_detail="Timeout ao contactar o servidor terceiro.",
            )
        except httpx.HTTPError as exc:
            return IntegrationTestResult(
                success=False,
                message="Falha na conexão",
                server=_safe_host(url),
                authentication=auth_label,
                error_detail=_safe_error(exc),
            )

        duration_ms = int((time.perf_counter() - started) * 1000)
        if response.status_code >= 400:
            return IntegrationTestResult(
                success=False,
                message="Falha na conexão",
                server=_safe_host(url),
                duration_ms=duration_ms,
                authentication=auth_label,
                error_detail=f"HTTP {response.status_code}",
            )

        return IntegrationTestResult(
            success=True,
            message="Arquivo HTTPS acessível",
            server=_safe_host(url),
            duration_ms=duration_ms,
            authentication=auth_label,
            permission=fmt.upper(),
        )

    async def sync(
        self,
        *,
        configuration: dict[str, Any],
        secrets: dict[str, Any],
    ) -> IntegrationSyncResult:
        started_at = datetime.now(UTC).isoformat()
        url = _url(configuration)
        if not url:
            finished = datetime.now(UTC).isoformat()
            return IntegrationSyncResult(
                success=False,
                mode="full",
                records_processed=0,
                message="URL do arquivo não configurada.",
                started_at=started_at,
                finished_at=finished,
            )
        if err := _url_scheme_error(url):
            finished = datetime.now(UTC).isoformat()
            return IntegrationSyncResult(
                success=False,
                mode="full",
                records_processed=0,
                message=err,
                started_at=started_at,
                finished_at=finished,
            )
        if err := _missing_auth_secret(configuration, secrets):
            finished = datetime.now(UTC).isoformat()
            return IntegrationSyncResult(
                success=False,
                mode="full",
                records_processed=0,
                message=err,
                started_at=started_at,
                finished_at=finished,
            )

        fmt = _format(configuration)
        encoding = (
            str(configuration.get("encoding") or "utf-8").strip() or "utf-8"
        )
        delimiter = str(configuration.get("delimiter") or ",").strip() or ","

        try:
            response = await self._download(
                url=url, configuration=configuration, secrets=secrets, method="GET"
            )
        except httpx.TimeoutException:
            finished = datetime.now(UTC).isoformat()
            return IntegrationSyncResult(
                success=False,
                mode="full",
                records_processed=0,
                message="Timeout ao baixar o arquivo.",
                started_at=started_at,
                finished_at=finished,
            )
        except httpx.HTTPError as exc:
            finished = datetime.now(UTC).isoformat()
            return IntegrationSyncResult(
                success=False,
                mode="full",
                records_processed=0,
                message=_safe_error(exc),
                started_at=started_at,
                finished_at=finished,
            )

        if response.status_code >= 400:
            finished = datetime.now(UTC).isoformat()
            return IntegrationSyncResult(
                success=False,
                mode="full",
                records_processed=0,
                message=f"HTTP {response.status_code} ao baixar o arquivo.",
                started_at=started_at,
                finished_at=finished,
            )

        content = response.content
        if len(content) > self._max_bytes:
            finished = datetime.now(UTC).isoformat()
            return IntegrationSyncResult(
                success=False,
                mode="full",
                records_processed=0,
                message=f"Arquivo excede o limite de {self._max_bytes} bytes.",
                started_at=started_at,
                finished_at=finished,
            )

        try:
            records = _parse_records(
                content, fmt=fmt, encoding=encoding, delimiter=delimiter
            )
        except _HttpFileError as exc:
            finished = datetime.now(UTC).isoformat()
            return IntegrationSyncResult(
                success=False,
                mode="full",
                records_processed=0,
                message=str(exc),
                started_at=started_at,
                finished_at=finished,
            )

        finished = datetime.now(UTC).isoformat()
        return IntegrationSyncResult(
            success=True,
            mode="full",
            records_processed=records,
            message=(
                f"HTTPS file pull: {records} registro(s) ({fmt.upper()}, "
                f"{encoding}) de {_safe_host(url)}."
            ),
            started_at=started_at,
            finished_at=finished,
        )

    async def _download(
        self,
        *,
        url: str,
        configuration: dict[str, Any],
        secrets: dict[str, Any],
        method: str,
    ) -> httpx.Response:
        timeout_ms = configuration.get("timeout_ms") or configuration.get("timeoutMs")
        try:
            timeout_s = max(1.0, float(timeout_ms) / 1000.0) if timeout_ms else 30.0
        except (TypeError, ValueError):
            timeout_s = 30.0

        headers = _build_headers(configuration, secrets)
        if method == "GET":
            # Prefer raw content for CSV; JSON Accept still fine for both.
            headers.setdefault("Accept", "*/*")

        last_exc: Exception | None = None
        for attempt in range(self._max_retries):
            try:
                async with httpx.AsyncClient(
                    timeout=timeout_s, follow_redirects=True
                ) as client:
                    response = await client.request(method, url, headers=headers)
                if response.status_code in {429, 500, 502, 503, 504} and attempt + 1 < (
                    self._max_retries
                ):
                    import asyncio

                    await asyncio.sleep(self._retry_backoff_seconds * (attempt + 1))
                    continue
                return response
            except httpx.TimeoutException:
                raise
            except httpx.HTTPError as exc:
                last_exc = exc
                if attempt + 1 >= self._max_retries:
                    raise
                import asyncio

                await asyncio.sleep(self._retry_backoff_seconds * (attempt + 1))
        assert last_exc is not None
        raise last_exc


class _HttpFileError(Exception):
    """Safe parse error (no secrets)."""


def _parse_records(
    content: bytes, *, fmt: str, encoding: str, delimiter: str
) -> int:
    try:
        text = content.decode(encoding)
    except UnicodeDecodeError as exc:
        raise _HttpFileError(f"Encoding '{encoding}' inválido para o arquivo.") from exc

    if fmt == "csv":
        if not text.strip():
            return 0
        reader = csv.reader(io.StringIO(text), delimiter=delimiter[:1] or ",")
        rows = list(reader)
        if not rows:
            return 0
        return max(0, len(rows) - 1)

    # JSON
    try:
        data = json.loads(text) if text.strip() else []
    except json.JSONDecodeError as exc:
        raise _HttpFileError("Conteúdo JSON inválido.") from exc

    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict):
        for key in ("items", "data", "results", "records"):
            value = data.get(key)
            if isinstance(value, list):
                return len(value)
        return 1
    return 0


def _url(configuration: dict[str, Any]) -> str:
    return str(configuration.get("url") or "").strip()


def _format(configuration: dict[str, Any]) -> str:
    raw = str(configuration.get("format") or "json").strip().lower()
    return raw if raw in {"json", "csv"} else "json"


def _url_scheme_error(url: str) -> str | None:
    try:
        parsed = urlparse(url)
    except Exception:
        return "URL inválida."
    if parsed.scheme not in {"http", "https"}:
        return "URL deve usar http ou https."
    if not parsed.netloc:
        return "URL inválida."
    return None


def _missing_auth_secret(
    configuration: dict[str, Any], secrets: dict[str, Any]
) -> str | None:
    auth = str(
        configuration.get("auth_type") or configuration.get("authType") or "none"
    ).lower()
    if auth == "bearer":
        token = (
            secrets.get("bearer_token")
            or secrets.get("access_token")
            or secrets.get("token")
        )
        if not token or not str(token).strip():
            return "Bearer token não configurado no backend."
    elif auth == "api_key":
        key = secrets.get("api_key") or secrets.get("apiKey")
        if not key or not str(key).strip():
            return "API key não configurada no backend."
    return None
