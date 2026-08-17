"""Resolve tenant from Host subdomain and bind request ContextVar."""

from __future__ import annotations

from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from src.config.settings import Settings, get_settings
from src.modules.tenants.dtos.tenant_dtos import TenantDto
from src.modules.tenants.queries.tenant_queries import GetTenantBySlugQuery
from src.shared.application.query_bus import QueryBus
from src.shared.infrastructure.exceptions import NotFoundError, ValidationError
from src.shared.infrastructure.tenant_context import bind_tenant, unbind_tenant
from src.shared.infrastructure.tenant_host import (
    apply_slug_alias,
    assert_host_base_domain_allowed,
    extract_tenant_slug_from_host,
)

_SKIP_PREFIXES = (
    "/health",
    "/ready",
    "/version",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/v1/billing/webhooks",
    "/api/v1/hub",
)


class TenantMiddleware(BaseHTTPMiddleware):
    """Bind tenant from Host first label for all API routes."""

    def __init__(
        self,
        app: Callable,
        *,
        query_bus: QueryBus,
        settings: Settings | None = None,
    ) -> None:
        super().__init__(app)
        self._query_bus = query_bus
        self._settings = settings or get_settings()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        if any(path == p or path.startswith(p + "/") for p in _SKIP_PREFIXES):
            return await call_next(request)

        host = request.headers.get("host")
        try:
            # Always enforce allowlist when configured (default includes localhost + openvizion.com).
            assert_host_base_domain_allowed(
                host,
                self._settings.tenant_base_domains,
                enforce=bool(self._settings.tenant_base_domains),
            )
            slug = apply_slug_alias(
                extract_tenant_slug_from_host(host),
                self._settings.slug_aliases,
            )
        except ValidationError as exc:
            return JSONResponse(
                status_code=422,
                content={"error": {"code": "validation_error", "message": exc.message}},
            )

        try:
            # Resolution uses SECURITY DEFINER resolve_tenant_by_slug (tenants SELECT closed).
            tenant: TenantDto = await self._query_bus.ask(GetTenantBySlugQuery(slug=slug))
        except NotFoundError:
            return JSONResponse(
                status_code=404,
                content={
                    "error": {
                        "code": "not_found",
                        "message": f"Unknown tenant: {slug}",
                    }
                },
            )
        except ValidationError as exc:
            return JSONResponse(
                status_code=422,
                content={"error": {"code": "validation_error", "message": exc.message}},
            )

        id_token, slug_token, name_token = bind_tenant(
            tenant.id,
            slug=tenant.slug,
            name=tenant.name,
        )
        request.state.tenant_id = tenant.id
        request.state.tenant_slug = tenant.slug
        request.state.tenant_name = tenant.name
        try:
            return await call_next(request)
        finally:
            unbind_tenant(id_token, slug_token, name_token)
