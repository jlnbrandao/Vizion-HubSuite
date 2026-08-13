"""OAuth 2.0 Client Credentials provider — tokens stay server-side only."""

from __future__ import annotations

import asyncio
import hashlib
import time
from typing import Any
from urllib.parse import urlparse

import httpx

from src.modules.integrations.providers.base import (
    IntegrationSyncResult,
    IntegrationTestResult,
)
from src.modules.integrations.providers.rest_provider import RestProvider


class OAuth2Provider:
    """ETAPA 3: Client Credentials + token cache/renewal + resource GET via RestProvider."""

    type = "oauth2"

    def __init__(
        self,
        *,
        rest_provider: RestProvider | None = None,
        skew_seconds: float = 30.0,
        token_timeout_seconds: float = 15.0,
    ) -> None:
        self._rest = rest_provider or RestProvider()
        self._skew_seconds = skew_seconds
        self._token_timeout_seconds = token_timeout_seconds
        # cache_key -> (access_token, expires_at_monotonic)
        self._token_cache: dict[str, tuple[str, float]] = {}
        self._lock = asyncio.Lock()

    async def test_connection(
        self,
        *,
        configuration: dict[str, Any],
        secrets: dict[str, Any],
    ) -> IntegrationTestResult:
        token_url = _cfg(configuration, "token_url", "tokenUrl")
        client_id = _cfg(configuration, "client_id", "clientId")
        endpoint = _cfg(configuration, "endpoint")
        scope = _cfg(configuration, "scope")
        grant_type = (
            _cfg(configuration, "grant_type", "grantType") or "client_credentials"
        ).lower()

        if grant_type != "client_credentials":
            return IntegrationTestResult(
                success=False,
                message="Falha na conexão",
                error_detail=(
                    "ETAPA 3 suporta apenas grant_type=client_credentials."
                ),
            )
        if not token_url or not client_id:
            return IntegrationTestResult(
                success=False,
                message="Falha na conexão",
                error_detail="Token URL e Client ID são obrigatórios.",
            )
        if not _secret(secrets, "client_secret", "clientSecret"):
            return IntegrationTestResult(
                success=False,
                message="Falha na conexão",
                error_detail="Client secret não configurado no backend.",
            )
        if not endpoint:
            return IntegrationTestResult(
                success=False,
                message="Falha na conexão",
                error_detail="Endpoint do recurso não configurado.",
            )

        started = time.perf_counter()
        try:
            access_token = await self.get_access_token(
                configuration=configuration, secrets=secrets
            )
        except _OAuthTokenError as exc:
            return IntegrationTestResult(
                success=False,
                message="Falha na conexão",
                server=_safe_host(token_url),
                authentication="OAuth 2.0",
                error_detail=str(exc),
            )

        rest_config = _resource_config(configuration, endpoint)
        result = await self._rest.test_connection(
            configuration=rest_config,
            secrets={"bearer_token": access_token},
        )
        duration_ms = int((time.perf_counter() - started) * 1000)

        if not result.success:
            return IntegrationTestResult(
                success=False,
                message="Falha na conexão",
                server=result.server or _safe_host(endpoint),
                duration_ms=duration_ms,
                authentication="OAuth 2.0",
                permission=scope or None,
                error_detail=result.error_detail or result.message,
            )

        return IntegrationTestResult(
            success=True,
            message="Conexão realizada com sucesso",
            server=result.server or _safe_host(endpoint),
            duration_ms=duration_ms,
            authentication="OAuth 2.0",
            permission=scope or result.permission,
        )

    async def sync(
        self,
        *,
        configuration: dict[str, Any],
        secrets: dict[str, Any],
    ) -> IntegrationSyncResult:
        endpoint = _cfg(configuration, "endpoint")
        if not endpoint:
            now = _iso_now()
            return IntegrationSyncResult(
                success=False,
                mode="full",
                records_processed=0,
                message="Endpoint do recurso não configurado.",
                started_at=now,
                finished_at=now,
            )
        try:
            access_token = await self.get_access_token(
                configuration=configuration, secrets=secrets
            )
        except _OAuthTokenError as exc:
            now = _iso_now()
            return IntegrationSyncResult(
                success=False,
                mode="full",
                records_processed=0,
                message=str(exc),
                started_at=now,
                finished_at=now,
            )

        rest_config = _resource_config(configuration, endpoint)
        return await self._rest.sync(
            configuration=rest_config,
            secrets={"bearer_token": access_token},
        )

    async def get_access_token(
        self,
        *,
        configuration: dict[str, Any],
        secrets: dict[str, Any],
        force_refresh: bool = False,
    ) -> str:
        """Return a cached access token or fetch a new one. Never log the token."""
        token_url = _cfg(configuration, "token_url", "tokenUrl")
        client_id = _cfg(configuration, "client_id", "clientId")
        scope = _cfg(configuration, "scope")
        client_secret = _secret(secrets, "client_secret", "clientSecret")
        if not token_url or not client_id or not client_secret:
            raise _OAuthTokenError("Não foi possível autenticar no servidor terceiro.")

        cache_key = _cache_key(token_url, client_id, scope)
        async with self._lock:
            if not force_refresh:
                cached = self._token_cache.get(cache_key)
                if cached is not None:
                    token, expires_at = cached
                    if time.monotonic() < expires_at - self._skew_seconds:
                        return token

            token, expires_in = await self._fetch_token(
                token_url=token_url,
                client_id=client_id,
                client_secret=client_secret,
                scope=scope,
            )
            self._token_cache[cache_key] = (
                token,
                time.monotonic() + max(expires_in, 60),
            )
            return token

    def clear_token_cache(self) -> None:
        self._token_cache.clear()

    async def _fetch_token(
        self,
        *,
        token_url: str,
        client_id: str,
        client_secret: str,
        scope: str,
    ) -> tuple[str, float]:
        data: dict[str, str] = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        }
        if scope:
            data["scope"] = scope

        try:
            async with httpx.AsyncClient(
                timeout=self._token_timeout_seconds,
                follow_redirects=True,
            ) as client:
                response = await client.post(
                    token_url,
                    data=data,
                    headers={
                        "Accept": "application/json",
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                )
        except httpx.TimeoutException as exc:
            raise _OAuthTokenError(
                "Timeout ao obter access token no servidor terceiro."
            ) from exc
        except httpx.HTTPError as exc:
            raise _OAuthTokenError(_safe_error(exc)) from exc

        if response.status_code >= 400:
            raise _OAuthTokenError(
                "Não foi possível autenticar no servidor terceiro "
                f"(HTTP {response.status_code})."
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise _OAuthTokenError(
                "Resposta inválida do token endpoint."
            ) from exc

        if not isinstance(payload, dict):
            raise _OAuthTokenError("Resposta inválida do token endpoint.")

        access_token = payload.get("access_token")
        if not access_token or not isinstance(access_token, str):
            raise _OAuthTokenError("Token endpoint não retornou access_token.")

        token_type = str(payload.get("token_type") or "Bearer").lower()
        if token_type != "bearer":
            raise _OAuthTokenError(f"token_type não suportado: {token_type}")

        try:
            expires_in = float(payload.get("expires_in") or 3600)
        except (TypeError, ValueError):
            expires_in = 3600.0

        return access_token, expires_in


class _OAuthTokenError(Exception):
    """Safe token acquisition error (no secrets in message)."""


def _resource_config(configuration: dict[str, Any], endpoint: str) -> dict[str, Any]:
    if endpoint.startswith("http://") or endpoint.startswith("https://"):
        return {
            "base_url": endpoint,
            "endpoint": endpoint,
            "http_method": "GET",
            "auth_type": "bearer",
            "timeout_ms": configuration.get("timeout_ms")
            or configuration.get("timeoutMs")
            or 30_000,
            "pagination": configuration.get("pagination") or "none",
            "rate_limit_per_minute": configuration.get("rate_limit_per_minute")
            or configuration.get("rateLimitPerMinute"),
            "headers": configuration.get("headers")
            if isinstance(configuration.get("headers"), dict)
            else {},
            "scope": _cfg(configuration, "scope"),
        }
    return {
        "base_url": _cfg(configuration, "base_url", "baseUrl"),
        "endpoint": endpoint or "/",
        "http_method": "GET",
        "auth_type": "bearer",
        "timeout_ms": configuration.get("timeout_ms")
        or configuration.get("timeoutMs")
        or 30_000,
        "pagination": configuration.get("pagination") or "none",
        "rate_limit_per_minute": configuration.get("rate_limit_per_minute")
        or configuration.get("rateLimitPerMinute"),
        "headers": configuration.get("headers")
        if isinstance(configuration.get("headers"), dict)
        else {},
        "scope": _cfg(configuration, "scope"),
    }


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


def _cache_key(token_url: str, client_id: str, scope: str) -> str:
    raw = f"{token_url}\0{client_id}\0{scope}".encode()
    return hashlib.sha256(raw).hexdigest()


def _safe_host(url: str) -> str:
    try:
        return urlparse(url).netloc or url
    except Exception:
        return url


def _safe_error(exc: Exception) -> str:
    text = str(exc).strip() or exc.__class__.__name__
    lowered = text.lower()
    for needle in ("client_secret", "authorization", "bearer ", "password"):
        if needle in lowered:
            return "Falha de rede ao contactar o token endpoint."
    if len(text) > 240:
        return text[:240] + "…"
    return text


def _iso_now() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).isoformat()
