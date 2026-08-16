"""Tracking FastAPI application."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from openvizion.observability.health import liveness_payload, readiness_payload, version_payload

from tracking.config import Settings, get_settings
from tracking.domain.errors import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    TrackingError,
    UnauthorizedError,
    ValidationError,
)
from tracking.infrastructure.composition import AppContainer, build_container
from tracking.infrastructure.security.middleware import ObservabilityMiddleware, TenantMiddleware
from tracking.interfaces.api.auth import router as auth_router
from tracking.interfaces.api.routes import router as tracking_router


def _error(status: int, exc: TrackingError) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"error": {"code": exc.code, "message": exc.message}},
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    container: AppContainer = app.state.container
    hub = container.hub
    if hub is not None:
        try:
            await hub.heartbeat(version=container.settings.app_version)
        except Exception:  # noqa: BLE001 — heartbeat must not block startup
            pass
    yield
    if hub is not None:
        await hub.aclose()
    await container.engine.dispose()


def create_app(container: AppContainer | None = None) -> FastAPI:
    settings = get_settings() if container is None else container.settings
    container = container or build_container(settings)

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
        docs_url="/docs" if settings.app_debug else None,
    )
    app.state.container = container
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.app_debug else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(TenantMiddleware, session_factory=container.session_factory)
    app.add_middleware(ObservabilityMiddleware, service=settings.service_name)

    @app.exception_handler(NotFoundError)
    async def not_found(_: Request, exc: NotFoundError) -> JSONResponse:
        return _error(404, exc)

    @app.exception_handler(ConflictError)
    async def conflict(_: Request, exc: ConflictError) -> JSONResponse:
        return _error(409, exc)

    @app.exception_handler(ValidationError)
    async def validation(_: Request, exc: ValidationError) -> JSONResponse:
        return _error(422, exc)

    @app.exception_handler(UnauthorizedError)
    async def unauthorized(_: Request, exc: UnauthorizedError) -> JSONResponse:
        return _error(401, exc)

    @app.exception_handler(ForbiddenError)
    async def forbidden(_: Request, exc: ForbiddenError) -> JSONResponse:
        return _error(403, exc)

    @app.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        return liveness_payload(app=settings.app_name, version=settings.app_version)

    @app.get("/version", tags=["system"])
    async def version() -> dict[str, str]:
        return version_payload(app=settings.app_name, version=settings.app_version)

    @app.get("/ready", tags=["system"])
    async def ready() -> JSONResponse:
        async def postgres() -> bool:
            async with container.engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return True

        body, status = await readiness_payload({"postgres": postgres})
        return JSONResponse(status_code=status, content=body)

    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(tracking_router, prefix="/api/v1")
    return app


app = create_app()
