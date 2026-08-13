"""Incremental sync provider — cursor / updated_since pull (httpx, server-side)."""

from __future__ import annotations

import asyncio
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
    RestProvider,
    _auth_label,
    _extract_cursor,
    _extract_items,
    _safe_error,
    _safe_host,
)


class IncrementalSyncProvider:
    """ETAPA 9: paginated pull with persisted cursor_value / updated_since."""

    type = "incremental_sync"

    def __init__(
        self,
        rest_provider: RestProvider | None = None,
        *,
        max_pages: int = 50,
    ) -> None:
        self._rest = rest_provider or RestProvider(max_pages=max_pages)
        self._max_pages = max_pages

    async def test_connection(
        self,
        *,
        configuration: dict[str, Any],
        secrets: dict[str, Any],
    ) -> IntegrationTestResult:
        base_url = _cfg(configuration, "base_url", "baseUrl")
        endpoint = _cfg(configuration, "endpoint") or "/"
        cursor_field = _cfg(configuration, "cursor_field", "cursorField") or "updated_since"
        if not base_url:
            return IntegrationTestResult(
                success=False,
                message="Falha na conexão",
                error_detail="URL base não configurada.",
            )
        if err := _missing_auth_secret(configuration, secrets):
            return IntegrationTestResult(
                success=False,
                message="Falha na conexão",
                error_detail=err,
            )

        page_size = _page_size(configuration)
        cursor_value = _cfg(configuration, "cursor_value", "cursorValue")
        params: dict[str, Any] = {"page_size": page_size, "limit": page_size}
        if cursor_value:
            params[cursor_field] = cursor_value

        url = _join(base_url, endpoint)
        auth_label = _auth_label(configuration)
        started = time.perf_counter()
        try:
            response = await self._rest._request(  # noqa: SLF001 — shared HTTP stack
                method="GET",
                url=url,
                configuration=configuration,
                secrets=secrets,
                params=params,
            )
        except httpx.TimeoutException:
            return IntegrationTestResult(
                success=False,
                message="Falha na conexão",
                server=_safe_host(base_url),
                authentication=auth_label,
                error_detail="Timeout ao contactar o servidor terceiro.",
            )
        except httpx.HTTPError as exc:
            return IntegrationTestResult(
                success=False,
                message="Falha na conexão",
                server=_safe_host(base_url),
                authentication=auth_label,
                error_detail=_safe_error(exc),
            )

        duration_ms = int((time.perf_counter() - started) * 1000)
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
            message="Endpoint incremental acessível",
            server=_safe_host(base_url),
            duration_ms=duration_ms,
            authentication=auth_label,
            permission=f"{cursor_field} · page {page_size}",
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
        cursor_field = _cfg(configuration, "cursor_field", "cursorField") or "updated_since"
        if not base_url:
            finished = datetime.now(UTC).isoformat()
            return IntegrationSyncResult(
                success=False,
                mode="incremental",
                records_processed=0,
                message="URL base não configurada.",
                started_at=started_at,
                finished_at=finished,
            )
        if err := _missing_auth_secret(configuration, secrets):
            finished = datetime.now(UTC).isoformat()
            return IntegrationSyncResult(
                success=False,
                mode="incremental",
                records_processed=0,
                message=err,
                started_at=started_at,
                finished_at=finished,
            )

        page_size = _page_size(configuration)
        cursor = _cfg(configuration, "cursor_value", "cursorValue") or None
        initial_cursor = cursor
        url = _join(base_url, endpoint)
        records = 0

        try:
            for _ in range(self._max_pages):
                params: dict[str, Any] = {
                    "page_size": page_size,
                    "limit": page_size,
                }
                if cursor:
                    params[cursor_field] = cursor

                response = await self._rest._request(  # noqa: SLF001
                    method="GET",
                    url=url,
                    configuration=configuration,
                    secrets=secrets,
                    params=params,
                )
                if response.status_code >= 400:
                    finished = datetime.now(UTC).isoformat()
                    return IntegrationSyncResult(
                        success=False,
                        mode="incremental",
                        records_processed=records,
                        message=f"HTTP {response.status_code} durante sync incremental",
                        started_at=started_at,
                        finished_at=finished,
                        cursor_value=cursor,
                    )

                batch = _extract_items(response)
                records += len(batch)

                next_cursor = _extract_cursor(response) or _max_item_cursor(
                    batch, cursor_field
                )
                if not batch:
                    break
                if not next_cursor or next_cursor == cursor:
                    # Advance using last page watermark when API omits next_cursor.
                    if len(batch) < page_size:
                        if next_cursor:
                            cursor = next_cursor
                        break
                    if not next_cursor:
                        break
                cursor = next_cursor
                if len(batch) < page_size:
                    break
                await asyncio.sleep(0)
        except httpx.HTTPError as exc:
            finished = datetime.now(UTC).isoformat()
            return IntegrationSyncResult(
                success=False,
                mode="incremental",
                records_processed=records,
                message=_safe_error(exc),
                started_at=started_at,
                finished_at=finished,
                cursor_value=cursor,
            )

        finished = datetime.now(UTC).isoformat()
        advanced = cursor if cursor and cursor != initial_cursor else cursor
        return IntegrationSyncResult(
            success=True,
            mode="incremental",
            records_processed=records,
            message=(
                f"Sync incremental: {records} registro(s); "
                f"cursor '{cursor_field}'="
                f"{advanced or '(inicial)'}."
            ),
            started_at=started_at,
            finished_at=finished,
            cursor_value=cursor,
        )


def _max_item_cursor(items: list[Any], cursor_field: str) -> str | None:
    """Derive next watermark from item fields (updated_since / updated_at / id)."""
    best: str | None = None
    aliases = (cursor_field, "updated_at", "updatedAt", "cursor", "id")
    for item in items:
        if not isinstance(item, dict):
            continue
        for key in aliases:
            value = item.get(key)
            if value is None or str(value).strip() == "":
                continue
            text = str(value).strip()
            if best is None or text > best:
                best = text
            break
    return best


def _page_size(configuration: dict[str, Any]) -> int:
    raw = configuration.get("page_size") or configuration.get("pageSize") or 100
    try:
        size = int(raw)
    except (TypeError, ValueError):
        size = 100
    return max(1, min(size, 1000))


def _missing_auth_secret(
    configuration: dict[str, Any], secrets: dict[str, Any]
) -> str | None:
    auth = (
        _cfg(configuration, "auth_type", "authType") or "none"
    ).strip().lower()
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


def _cfg(configuration: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = configuration.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _join(base_url: str, endpoint: str) -> str:
    if endpoint.startswith("http://") or endpoint.startswith("https://"):
        return endpoint
    return urljoin(base_url.rstrip("/") + "/", endpoint.lstrip("/"))
