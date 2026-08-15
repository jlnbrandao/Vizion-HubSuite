"""ASGI middleware — baseline HTTP security headers.

The API answers JSON only, so the default CSP denies every fetch directive.
Swagger/ReDoc (development only) need a relaxed policy to load their bundles.
"""

from __future__ import annotations

from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from src.config.settings import Settings, get_settings

_DOCS_PATHS = ("/docs", "/redoc", "/openapi.json")

_API_CSP = (
    "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
)
_DOCS_CSP = (
    "default-src 'none'; "
    "script-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
    "style-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
    "img-src 'self' https://fastapi.tiangolo.com data:; "
    "font-src 'self' https://cdn.jsdelivr.net; "
    "connect-src 'self'; "
    "frame-ancestors 'none'; base-uri 'none'"
)

_STATIC_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "geolocation=(), camera=(), microphone=(), payment=()",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
    "X-Permitted-Cross-Domain-Policies": "none",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: Callable, settings: Settings | None = None) -> None:
        super().__init__(app)
        self._settings = settings or get_settings()

    def _hsts_value(self) -> str:
        parts = [f"max-age={self._settings.hsts_max_age}"]
        if self._settings.hsts_include_subdomains:
            parts.append("includeSubDomains")
        if self._settings.hsts_preload:
            parts.append("preload")
        return "; ".join(parts)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        if not self._settings.security_headers_enabled:
            return response

        for header, value in _STATIC_HEADERS.items():
            response.headers.setdefault(header, value)

        path = request.url.path
        is_docs = any(path == p or path.startswith(p + "/") for p in _DOCS_PATHS)
        response.headers.setdefault(
            "Content-Security-Policy", _DOCS_CSP if is_docs else _API_CSP
        )

        if self._settings.hsts_active:
            response.headers.setdefault("Strict-Transport-Security", self._hsts_value())

        # Credentialed API responses must never land in a shared cache.
        if "authorization" in request.headers or request.cookies:
            response.headers.setdefault("Cache-Control", "no-store")

        return response
