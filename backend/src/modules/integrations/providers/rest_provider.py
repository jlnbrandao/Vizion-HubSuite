"""REST outbound provider — real HTTP via httpx (server-side only)."""

from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

from src.modules.integrations.providers.base import (
    IntegrationSyncResult,
    IntegrationTestResult,
)


class RestProvider:
    """ETAPA 2: GET with headers, auth, timeout, pagination, rate limit, retry."""

    type = "rest"

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
        base_url = str(configuration.get("base_url") or configuration.get("baseUrl") or "").strip()
        endpoint = str(configuration.get("endpoint") or "/").strip() or "/"
        if not base_url:
            return IntegrationTestResult(
                success=False,
                message="Falha na conexão",
                error_detail="URL base não configurada.",
            )

        raw_method = (
            configuration.get("http_method") or configuration.get("httpMethod") or "GET"
        )
        method = str(raw_method).upper()
        if method not in {"GET", "HEAD"}:
            # Connection test stays read-only.
            method = "GET"

        started = time.perf_counter()
        try:
            response = await self._request(
                method=method,
                url=self._join(base_url, endpoint),
                configuration=configuration,
                secrets=secrets,
            )
        except httpx.TimeoutException:
            return IntegrationTestResult(
                success=False,
                message="Falha na conexão",
                server=_safe_host(base_url),
                error_detail="Timeout ao contactar o servidor terceiro.",
            )
        except httpx.HTTPError as exc:
            return IntegrationTestResult(
                success=False,
                message="Falha na conexão",
                server=_safe_host(base_url),
                error_detail=_safe_error(exc),
            )

        duration_ms = int((time.perf_counter() - started) * 1000)
        auth_label = _auth_label(configuration)
        if response.status_code >= 400:
            return IntegrationTestResult(
                success=False,
                message="Falha na conexão",
                server=_safe_host(base_url),
                duration_ms=duration_ms,
                authentication=auth_label,
                error_detail=f"HTTP {response.status_code}",
            )

        return IntegrationTestResult(
            success=True,
            message="Conexão realizada com sucesso",
            server=_safe_host(base_url),
            duration_ms=duration_ms,
            authentication=auth_label,
            permission=_permission_hint(configuration, response),
        )

    async def sync(
        self,
        *,
        configuration: dict[str, Any],
        secrets: dict[str, Any],
    ) -> IntegrationSyncResult:
        started_at = datetime.now(UTC).isoformat()
        base_url = str(configuration.get("base_url") or configuration.get("baseUrl") or "").strip()
        endpoint = str(configuration.get("endpoint") or "/").strip() or "/"
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
        url = self._join(base_url, endpoint)

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
                    secrets=secrets,
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
        except httpx.HTTPError as exc:
            finished = datetime.now(UTC).isoformat()
            return IntegrationSyncResult(
                success=False,
                mode="full" if pagination == "none" else "incremental",
                records_processed=records,
                message=_safe_error(exc),
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
        secrets: dict[str, Any],
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:
        timeout_ms = configuration.get("timeout_ms") or configuration.get("timeoutMs") or 30_000
        try:
            timeout_s = max(float(timeout_ms) / 1000.0, 1.0)
        except (TypeError, ValueError):
            timeout_s = 30.0

        headers = _build_headers(configuration, secrets)
        last_exc: Exception | None = None

        async with httpx.AsyncClient(timeout=timeout_s, follow_redirects=True) as client:
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
                except (httpx.TimeoutException, httpx.TransportError) as exc:
                    last_exc = exc
                    if attempt >= self._max_retries:
                        raise
                    await asyncio.sleep(self._retry_backoff_seconds * (2**attempt))

        assert last_exc is not None
        raise last_exc

    @staticmethod
    def _join(base_url: str, endpoint: str) -> str:
        if endpoint.startswith("http://") or endpoint.startswith("https://"):
            return endpoint
        return urljoin(base_url.rstrip("/") + "/", endpoint.lstrip("/"))


def _build_headers(configuration: dict[str, Any], secrets: dict[str, Any]) -> dict[str, str]:
    headers: dict[str, str] = {"Accept": "application/json"}
    raw_headers = configuration.get("headers")
    if isinstance(raw_headers, dict):
        for key, value in raw_headers.items():
            if value is None:
                continue
            headers[str(key)] = str(value)

    auth_raw = configuration.get("auth_type") or configuration.get("authType") or "none"
    auth_type = str(auth_raw).lower()
    if auth_type == "bearer":
        token = (
            secrets.get("bearer_token")
            or secrets.get("access_token")
            or secrets.get("token")
        )
        if token:
            headers["Authorization"] = f"Bearer {token}"
    elif auth_type == "api_key":
        api_key = secrets.get("api_key") or secrets.get("apiKey")
        header_name = str(
            configuration.get("api_key_header")
            or configuration.get("apiKeyHeader")
            or "X-API-Key"
        )
        if api_key:
            headers[header_name] = str(api_key)
    return headers


def _auth_label(configuration: dict[str, Any]) -> str:
    auth_type = str(configuration.get("auth_type") or configuration.get("authType") or "none")
    if auth_type == "none":
        return "Nenhuma"
    return auth_type


def _permission_hint(configuration: dict[str, Any], response: httpx.Response) -> str:
    scope = configuration.get("scope")
    if scope:
        return str(scope)
    return f"HTTP {response.status_code}"


def _extract_items(response: httpx.Response) -> list[Any]:
    try:
        data = response.json()
    except ValueError:
        text = response.text or ""
        return [text] if text else []

    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("items", "data", "results", "records"):
            value = data.get(key)
            if isinstance(value, list):
                return value
        return [data]
    return []


def _extract_cursor(response: httpx.Response) -> str | None:
    try:
        data = response.json()
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None
    for key in ("next_cursor", "nextCursor", "cursor"):
        value = data.get(key)
        if value:
            return str(value)
    next_page = data.get("next") or data.get("next_page")
    return str(next_page) if next_page else None


def _safe_host(url: str) -> str:
    try:
        return urlparse(url).netloc or url
    except Exception:
        return url


def _safe_error(exc: Exception) -> str:
    # Never include request headers/secrets — message only.
    text = str(exc).strip() or exc.__class__.__name__
    if len(text) > 240:
        return text[:240] + "…"
    return text
