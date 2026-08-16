from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from openvizion.kernel.identity import TenantInfo
from openvizion.observability.context import (
    CORRELATION_ID_HEADER,
    REQUEST_ID_HEADER,
    bind_context,
    reset_context,
)

from tracking.infrastructure.database.models import TenantModel
from tracking.infrastructure.security.tenant import bind_tenant, extract_slug, unbind_tenant

_SKIP = ("/health", "/ready", "/version", "/docs", "/redoc", "/openapi.json")


class ObservabilityMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: Callable, *, service: str) -> None:
        super().__init__(app)
        self._service = service

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        token, ctx = bind_context(
            request_id=request.headers.get(REQUEST_ID_HEADER),
            correlation_id=request.headers.get(CORRELATION_ID_HEADER),
            service=self._service,
        )
        try:
            response = await call_next(request)
        finally:
            reset_context(token)
        response.headers.setdefault(REQUEST_ID_HEADER, ctx.request_id)
        response.headers.setdefault(CORRELATION_ID_HEADER, ctx.correlation_id)
        return response


class TenantMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: Callable, *, session_factory: async_sessionmaker[AsyncSession]) -> None:
        super().__init__(app)
        self._session_factory = session_factory

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        if any(path == item or path.startswith(item + "/") for item in _SKIP):
            return await call_next(request)
        try:
            slug = extract_slug(request.headers.get("host"))
        except ValueError as exc:
            return JSONResponse(
                status_code=422,
                content={"error": {"code": "validation_error", "message": str(exc)}},
            )
        async with self._session_factory() as session:
            result = await session.execute(select(TenantModel).where(TenantModel.slug == slug))
            row = result.scalar_one_or_none()
        if row is None:
            return JSONResponse(
                status_code=404,
                content={"error": {"code": "not_found", "message": f"Unknown tenant: {slug}"}},
            )
        tenant = TenantInfo(id=row.id, slug=row.slug, name=row.name, is_active=row.is_active)
        token = bind_tenant(tenant)
        request.state.tenant_id = tenant.id
        try:
            return await call_next(request)
        finally:
            unbind_tenant(token)
