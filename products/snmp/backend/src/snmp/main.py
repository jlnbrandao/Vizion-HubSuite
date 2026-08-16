"""SNMP FastAPI scaffold — kernel + health only, no domain."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from openvizion.kernel.configuration import AdapterSelection
from openvizion.kernel.hub import HubPlatformAdapter
from openvizion.observability.health import liveness_payload, readiness_payload, version_payload

from snmp.config import Settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    hub: HubPlatformAdapter | None = getattr(app.state, "hub", None)
    if hub is not None:
        try:
            await hub.heartbeat(version=app.state.settings.app_version)
        except Exception:  # noqa: BLE001 — heartbeat must not block startup
            pass
    yield
    if hub is not None:
        await hub.aclose()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    settings.validate_mode()
    hub: HubPlatformAdapter | None = None
    if settings.platform_adapter == AdapterSelection.HUB:
        hub = HubPlatformAdapter(
            base_url=settings.platform_core_url,
            client_id=settings.platform_client_id,
            client_secret=settings.platform_client_secret,
        )

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
        docs_url="/docs" if settings.app_debug else None,
    )
    app.state.settings = settings
    app.state.hub = hub

    @app.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        return liveness_payload(app=settings.app_name, version=settings.app_version)

    @app.get("/version", tags=["system"])
    async def version() -> dict[str, str]:
        return version_payload(app=settings.app_name, version=settings.app_version)

    @app.get("/ready", tags=["system"])
    async def ready() -> JSONResponse:
        body, status = await readiness_payload({})
        return JSONResponse(status_code=status, content=body)

    @app.get("/api/v1/status", tags=["system"])
    async def status() -> dict[str, str]:
        return {
            "product": "snmp",
            "mode": settings.deployment_mode.value,
            "adapter": settings.platform_adapter.value,
        }

    return app


app = create_app()
