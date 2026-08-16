"""HubPlatformAdapter — HTTP client for Platform Core hub contracts.

Timeouts, bounded retries and fail-closed entitlement/authz after cache expiry.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID
from urllib.parse import urljoin

import httpx

from openvizion.kernel.identity import Principal, TenantInfo

_RETRY_STATUS = frozenset({502, 503, 504})


class HubUnavailableError(Exception):
    """Platform Core did not answer in time or returned a retryable failure."""


class HubPlatformAdapter:
    def __init__(
        self,
        *,
        base_url: str,
        client_id: str,
        client_secret: str,
        timeout_seconds: float = 5.0,
        retries: int = 2,
        cache_ttl_seconds: float = 30.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not base_url.strip():
            raise ValueError("PLATFORM_CORE_URL is required for HubPlatformAdapter")
        self._base_url = base_url.rstrip("/") + "/"
        self._client_id = client_id
        self._client_secret = client_secret
        self._timeout = timeout_seconds
        self._retries = retries
        self._cache_ttl = timedelta(seconds=cache_ttl_seconds)
        self._client = client
        self._owns_client = client is None
        self._service_token: str | None = None
        self._entitlement_cache: dict[tuple[UUID, str], tuple[bool, datetime]] = {}
        self._authz_cache: dict[tuple[UUID, str], tuple[bool, datetime]] = {}

    async def aclose(self) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    def _http(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._timeout)
        return self._client

    def _url(self, path: str) -> str:
        return urljoin(self._base_url, path.lstrip("/"))

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        authenticated: bool = True,
    ) -> httpx.Response:
        req_headers = dict(headers or {})
        if authenticated:
            token = await self._service_access_token()
            req_headers["Authorization"] = f"Bearer {token}"
        last_error: Exception | None = None
        attempts = self._retries + 1
        for attempt in range(attempts):
            try:
                response = await self._http().request(
                    method,
                    self._url(path),
                    json=json,
                    headers=req_headers,
                )
            except httpx.TimeoutException as exc:
                last_error = exc
                if attempt + 1 < attempts:
                    await asyncio.sleep(0.05 * (attempt + 1))
                    continue
                raise HubUnavailableError("Platform Core timed out") from exc
            except httpx.RequestError as exc:
                last_error = exc
                if attempt + 1 < attempts:
                    await asyncio.sleep(0.05 * (attempt + 1))
                    continue
                raise HubUnavailableError("Platform Core unreachable") from exc
            if response.status_code in _RETRY_STATUS and attempt + 1 < attempts:
                await asyncio.sleep(0.05 * (attempt + 1))
                continue
            return response
        raise HubUnavailableError("Platform Core unreachable") from last_error

    async def _service_access_token(self) -> str:
        if self._service_token:
            return self._service_token
        response = await self._request(
            "POST",
            "/api/v1/hub/token",
            json={"client_id": self._client_id, "client_secret": self._client_secret},
            authenticated=False,
        )
        if response.status_code >= 400:
            raise HubUnavailableError("Platform Core rejected service credentials")
        self._service_token = str(response.json()["access_token"])
        return self._service_token

    def _cache_get(
        self,
        cache: dict[tuple[UUID, str], tuple[bool, datetime]],
        key: tuple[UUID, str],
    ) -> bool | None:
        hit = cache.get(key)
        if hit is None:
            return None
        value, expires = hit
        if datetime.now(UTC) >= expires:
            cache.pop(key, None)
            return None
        return value

    def _cache_put(
        self,
        cache: dict[tuple[UUID, str], tuple[bool, datetime]],
        key: tuple[UUID, str],
        value: bool,
    ) -> None:
        cache[key] = (value, datetime.now(UTC) + self._cache_ttl)

    async def get_current_user(self, access_token: str) -> Principal:
        response = await self._request(
            "POST",
            "/api/v1/hub/introspect",
            json={"token": access_token},
        )
        if response.status_code == 401:
            raise PermissionError("Invalid access token")
        if response.status_code >= 400:
            raise HubUnavailableError("Platform Core introspect failed")
        body = response.json()
        return Principal(
            id=UUID(body["id"]),
            email=body["email"],
            full_name=body["full_name"],
            tenant_id=UUID(body["tenant_id"]),
            tenant_slug=body["tenant_slug"],
            tenant_name=body.get("tenant_name") or "",
            role_names=frozenset(body.get("role_names") or []),
            permissions=frozenset(body.get("permissions") or []),
        )

    async def get_tenant(self, tenant_id: UUID) -> TenantInfo:
        response = await self._request("GET", f"/api/v1/hub/tenants/{tenant_id}")
        if response.status_code == 404:
            raise KeyError(str(tenant_id))
        if response.status_code >= 400:
            raise HubUnavailableError("Platform Core tenant lookup failed")
        body = response.json()
        return TenantInfo(
            id=UUID(body["id"]),
            slug=body["slug"],
            name=body["name"],
            is_active=bool(body.get("is_active", True)),
        )

    async def authorize(
        self,
        principal: Principal,
        action: str,
        *,
        resource_type: str | None = None,
        resource_id: UUID | None = None,
    ) -> bool:
        cached = self._cache_get(self._authz_cache, (principal.id, action))
        if cached is not None:
            return cached
        try:
            response = await self._request(
                "POST",
                "/api/v1/hub/authorize",
                json={
                    "user_id": str(principal.id),
                    "tenant_id": str(principal.tenant_id),
                    "action": action,
                    "resource_type": resource_type,
                    "resource_id": str(resource_id) if resource_id else None,
                },
            )
        except HubUnavailableError:
            return False
        if response.status_code >= 400:
            return False
        allowed = bool(response.json().get("allowed"))
        self._cache_put(self._authz_cache, (principal.id, action), allowed)
        return allowed

    async def check_entitlement(self, tenant_id: UUID, capability: str) -> bool:
        cached = self._cache_get(self._entitlement_cache, (tenant_id, capability))
        if cached is not None:
            return cached
        try:
            response = await self._request(
                "POST",
                "/api/v1/hub/entitlements/check",
                json={"tenant_id": str(tenant_id), "capability": capability},
            )
        except HubUnavailableError:
            return False
        if response.status_code >= 400:
            return False
        entitled = bool(response.json().get("entitled"))
        self._cache_put(self._entitlement_cache, (tenant_id, capability), entitled)
        return entitled

    async def audit(
        self,
        *,
        action: str,
        principal: Principal | None,
        resource_type: str | None = None,
        resource_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        try:
            await self._request(
                "POST",
                "/api/v1/hub/audit",
                json={
                    "action": action,
                    "user_id": str(principal.id) if principal else None,
                    "tenant_id": str(principal.tenant_id) if principal else None,
                    "resource_type": resource_type,
                    "resource_id": str(resource_id) if resource_id else None,
                    "metadata": metadata or {},
                },
            )
        except HubUnavailableError:
            return

    async def publish_event(
        self,
        *,
        event_type: str,
        tenant_id: UUID,
        payload: dict[str, Any],
        correlation_id: str | None = None,
    ) -> None:
        try:
            await self._request(
                "POST",
                "/api/v1/hub/events",
                json={
                    "event_type": event_type,
                    "tenant_id": str(tenant_id),
                    "payload": payload,
                    "correlation_id": correlation_id,
                },
            )
        except HubUnavailableError:
            return

    async def login(
        self,
        *,
        login: str,
        password: str,
        tenant_host: str,
    ) -> dict[str, Any]:
        """Forward credentials to Platform Core. Used only at login, not in domain."""
        response = await self._http().post(
            self._url("/api/v1/auth/login"),
            json={"login": login, "password": password},
            headers={"Host": tenant_host},
        )
        if response.status_code >= 400:
            raise PermissionError("Invalid credentials")
        return response.json()

    async def heartbeat(self, *, version: str, status: str = "ok") -> None:
        await self._request(
            "POST",
            "/api/v1/hub/heartbeat",
            json={"version": version, "status": status},
        )
