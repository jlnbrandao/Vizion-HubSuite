"""ASGI middleware — rate limit by tenant + client IP (skips health + docs)."""

from __future__ import annotations

from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from src.shared.infrastructure.security.client_ip import client_ip_from_request
from src.shared.infrastructure.security.rate_limiter import RateLimiter
from src.shared.infrastructure.tenant_context import get_current_tenant_slug

_SKIP_PREFIXES = ("/health", "/docs", "/redoc", "/openapi.json")


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: Callable, rate_limiter: RateLimiter) -> None:
        super().__init__(app)
        self._rate_limiter = rate_limiter

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        if any(path == p or path.startswith(p + "/") for p in _SKIP_PREFIXES):
            return await call_next(request)

        client_ip = client_ip_from_request(request)
        tenant_slug = getattr(request.state, "tenant_slug", None) or get_current_tenant_slug()
        key = f"{tenant_slug or 'unknown'}:{client_ip}"
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
