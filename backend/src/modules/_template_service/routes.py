"""Example routes for a service slice.

Two things make this a Hub service rather than an endpoint that happens to exist:
`require_permission` with a namespaced code (the engine then checks the tenant's
entitlement for `template`), and `ServiceQuotaGuard` on the metered operation.
"""

from __future__ import annotations

from typing import Any

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.modules.services.quotas import ServiceQuotaGuard
from src.shared.infrastructure.di.container import Container
from src.shared.infrastructure.security.current_user import CurrentUser
from src.shared.infrastructure.security.dependencies import require_permission

#: Permission namespace == service slug == `services.namespace` in the catalog.
SERVICE_NAMESPACE = "template"

router = APIRouter(prefix="/template", tags=["template-service"])


class TemplateResourceResponse(BaseModel):
    code: str
    name: str


@router.get("/resources", response_model=list[TemplateResourceResponse])
@inject
async def list_resources(
    _: CurrentUser = Depends(require_permission(f"{SERVICE_NAMESPACE}.resources.read")),
    uow_factory: Any = Depends(Provide[Container.unit_of_work]),
) -> list[TemplateResourceResponse]:
    async with uow_factory:
        return []


@router.post("/resources/sync", response_model=dict[str, int])
@inject
async def sync_resources(
    actor: CurrentUser = Depends(require_permission(f"{SERVICE_NAMESPACE}.resources.sync")),
    quotas: ServiceQuotaGuard = Depends(Provide[Container.service_quota_guard]),
) -> dict[str, int]:
    """Metered operation: the tenant's plan decides how often it may run."""
    remaining = await quotas.enforce(
        tenant_id=actor.tenant_id,
        namespace=SERVICE_NAMESPACE,
        metric="sync_per_hour",
        window_seconds=3600,
    )
    return {"synced": 0, "remaining": remaining}
