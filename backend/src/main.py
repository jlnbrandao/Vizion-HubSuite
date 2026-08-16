"""FastAPI application factory and lifespan.

API Gateway: CORS → Rate Limit → routes with JWT AuthN + RBAC AuthZ.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from src.config.settings import get_settings
from src.modules.authentication.routes.auth_routes import router as auth_router
from src.modules.billing.routes import router as billing_router
from src.modules.dashboard.routes.dashboard_routes import router as dashboard_router
from src.modules.iam.routes import router as iam_router
from src.modules.iam.scim.routes import router as scim_router
from src.modules.integrations.routes import router as integrations_router
from src.modules.navigation.routes import router as navigation_router
from src.modules.permissions.routes.permission_group_routes import (
    router as permission_bundles_router,
)
from src.modules.permissions.routes.permission_routes import router as permissions_router
from src.modules.products.routes import admin_router as products_admin_router
from src.modules.products.routes import hub_router as products_hub_router
from src.modules.roles.routes.role_routes import router as roles_router
from src.modules.services.routes import router as services_router
from src.modules.services.usage_routes import router as usage_router
from src.modules.tenants.routes.tenant_routes import router as tenants_router
from src.modules.users.routes.user_routes import router as users_router
from src.shared.infrastructure.audit_handlers import register_audit_handlers
from src.shared.infrastructure.di.container import Container, create_container
from src.shared.infrastructure.di.register_handlers import register_module_handlers
from src.shared.infrastructure.exceptions import (
    ApplicationError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ServiceUnavailableError,
    UnauthorizedError,
    ValidationError,
)
from src.shared.infrastructure.request_context import REQUEST_ID_HEADER
from src.shared.infrastructure.request_id_middleware import RequestIdMiddleware
from src.shared.infrastructure.security.rate_limit_middleware import RateLimitMiddleware
from src.shared.infrastructure.security.security_headers_middleware import (
    SecurityHeadersMiddleware,
)
from src.shared.infrastructure.security.tenant_middleware import TenantMiddleware


def _error_response(status_code: int, exc: ApplicationError) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
    )


_WIRE_MODULES = [
    "src.modules.permissions.routes.permission_routes",
    "src.modules.permissions.routes.permission_group_routes",
    "src.modules.roles.routes.role_routes",
    "src.modules.users.routes.user_routes",
    "src.modules.tenants.routes.tenant_routes",
    "src.modules.authentication.routes.auth_routes",
    "src.modules.dashboard.routes.dashboard_routes",
    "src.modules.navigation.routes",
    "src.modules.services.routes",
    "src.modules.services.usage_routes",
    "src.modules.iam.routes",
    "src.modules.iam.scim.routes",
    "src.modules.integrations.routes",
    "src.modules.billing.routes",
    "src.modules.products.routes",
    "src.shared.infrastructure.security.dependencies",
]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    container: Container = app.state.container
    register_module_handlers(container)
    register_audit_handlers(container.event_bus(), container)
    yield
    engine = container.engine()
    await engine.dispose()
    redis = container.redis()
    await redis.aclose()


def create_app(container: Container | None = None) -> FastAPI:
    settings = get_settings()
    container = container or create_container()

    docs_url = "/docs" if settings.is_development else None
    redoc_url = "/redoc" if settings.is_development else None
    openapi_url = "/openapi.json" if settings.is_development else None

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        debug=settings.app_debug,
        lifespan=lifespan,
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
    )
    app.state.container = container
    container.wire(modules=_WIRE_MODULES)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.is_development else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[REQUEST_ID_HEADER],
    )
    # Last added runs first: RequestId → Tenant → RateLimit → SecurityHeaders → CORS
    app.add_middleware(SecurityHeadersMiddleware, settings=settings)
    app.add_middleware(
        RateLimitMiddleware,
        rate_limiter=container.rate_limiter(),
        settings=settings,
    )
    app.add_middleware(
        TenantMiddleware,
        query_bus=container.query_bus(),
        settings=settings,
    )
    # Outermost: every audit event of the request, tenant resolution included,
    # must be able to reference the same correlation id.
    app.add_middleware(RequestIdMiddleware)

    @app.exception_handler(NotFoundError)
    async def not_found_handler(_: Request, exc: NotFoundError) -> JSONResponse:
        return _error_response(404, exc)

    @app.exception_handler(ConflictError)
    async def conflict_handler(_: Request, exc: ConflictError) -> JSONResponse:
        return _error_response(409, exc)

    @app.exception_handler(ValidationError)
    async def validation_handler(_: Request, exc: ValidationError) -> JSONResponse:
        return _error_response(422, exc)

    @app.exception_handler(UnauthorizedError)
    async def unauthorized_handler(_: Request, exc: UnauthorizedError) -> JSONResponse:
        return _error_response(401, exc)

    @app.exception_handler(ForbiddenError)
    async def forbidden_handler(_: Request, exc: ForbiddenError) -> JSONResponse:
        return _error_response(403, exc)

    @app.exception_handler(ServiceUnavailableError)
    async def unavailable_handler(_: Request, exc: ServiceUnavailableError) -> JSONResponse:
        return _error_response(503, exc)

    @app.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "app": settings.app_name, "version": app.version}

    @app.get("/version", tags=["system"])
    async def version() -> dict[str, str]:
        return {"app": settings.app_name, "version": app.version}

    @app.get("/ready", tags=["system"])
    async def ready() -> JSONResponse:
        checks: dict[str, str] = {}
        try:
            async with container.engine().connect() as conn:
                await conn.execute(text("SELECT 1"))
            checks["postgres"] = "ok"
        except Exception:  # noqa: BLE001
            checks["postgres"] = "fail"
        try:
            pong = await container.redis().ping()
            checks["redis"] = "ok" if pong else "fail"
        except Exception:  # noqa: BLE001
            checks["redis"] = "fail"
        ok = all(value == "ok" for value in checks.values())
        return JSONResponse(
            status_code=200 if ok else 503,
            content={"status": "ok" if ok else "degraded", "checks": checks},
        )

    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(dashboard_router, prefix="/api/v1")
    app.include_router(navigation_router, prefix="/api/v1")
    app.include_router(services_router, prefix="/api/v1")
    app.include_router(usage_router, prefix="/api/v1")
    app.include_router(permissions_router, prefix="/api/v1")
    app.include_router(permission_bundles_router, prefix="/api/v1")
    app.include_router(roles_router, prefix="/api/v1")
    app.include_router(users_router, prefix="/api/v1")
    app.include_router(tenants_router, prefix="/api/v1")
    app.include_router(iam_router, prefix="/api/v1")
    app.include_router(scim_router, prefix="/api/v1")
    app.include_router(integrations_router, prefix="/api/v1")
    app.include_router(billing_router, prefix="/api/v1")
    app.include_router(products_admin_router, prefix="/api/v1")
    app.include_router(products_hub_router, prefix="/api/v1")

    return app


app = create_app()
