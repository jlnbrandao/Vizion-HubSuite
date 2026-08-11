"""ASGI middleware — rate limit by tenant + client IP (skips health + docs)."""

from __future__ import annotations

from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from src.config.settings import Settings, get_settings
from src.shared.infrastructure.security.client_ip import client_ip_from_request
from src.shared.infrastructure.security.rate_limiter import RateLimiter
from src.shared.infrastructure.tenant_context import get_current_tenant_slug

_SKIP_PREFIXES = ("/health", "/docs", "/redoc", "/openapi.json")
_AUTH_PATHS = (
    "/api/v1/auth/login",
    "/api/v1/auth/refresh",
)


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: Callable,
        rate_limiter: RateLimiter,
        settings: Settings | None = None,
    ) -> None:
        super().__init__(app)
        self._rate_limiter = rate_limiter
        self._settings = settings or get_settings()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        if any(path == p or path.startswith(p + "/") for p in _SKIP_PREFIXES):
            return await call_next(request)

        client_ip = client_ip_from_request(request)
        tenant_slug = getattr(request.state, "tenant_slug", None) or get_current_tenant_slug()
        is_auth = path in _AUTH_PATHS
        prefix = "auth" if is_auth else "api"
        key = f"{prefix}:{tenant_slug or 'unknown'}:{client_ip}"

        if is_auth:
            # Temporary override window/limit via a dedicated limiter call:
            # RateLimiter uses settings from construction; use a second check with
            # a composite key and lower budget by consuming from a stricter bucket.
            allowed, remaining = await self._rate_limiter.is_allowed(
                key,
                limit=self._settings.auth_rate_limit_requests,
                window_seconds=self._settings.auth_rate_limit_window_seconds,
            )
        else:
            allowed, remaining = await self._rate_limiter.is_allowed(key)

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "rate_limit_exceeded",
                        "message": "Too many requests",
                    }
                },
                headers={"Retry-After": "60", "X-RateLimit-Remaining": "0"},
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
