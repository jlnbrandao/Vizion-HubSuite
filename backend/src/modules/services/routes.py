"""Service catalog HTTP routes.

Tenant-facing: what my tenant is entitled to. Platform-facing: attach, suspend
and quota services for any tenant.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from src.modules.services.models import TENANT_SERVICE_STATUSES
from src.modules.services.service import (
    PlatformServiceCatalog,
    ServiceCatalogService,
    TenantServiceView,
)
from src.shared.infrastructure.di.container import Container
from src.shared.infrastructure.security.authorization_adapters import (
    CatalogEntitlementProvider,
)
from src.shared.infrastructure.security.current_user import CurrentUser
from src.shared.infrastructure.security.dependencies import (
    get_current_user,
    require_permission,
)
from src.shared.infrastructure.security.permission_codes import PermissionCode

router = APIRouter(prefix="/services", tags=["services"])


class ServiceResponse(BaseModel):
    slug: str
    namespace: str
    name: str
    description: str
    version: str
    is_core: bool
    is_active: bool


class TenantServiceResponse(BaseModel):
    slug: str
    namespace: str
    name: str
    description: str
    version: str
    is_core: bool
    is_active: bool
    #: None when the tenant has no contract for this service.
    status: str | None = None
    plan: str | None = None
    entitled: bool
    quotas: dict[str, Any] = Field(default_factory=dict)
    expires_at: datetime | None = None


class SetTenantServiceRequest(BaseModel):
    status: str = Field(description=f"One of: {', '.join(sorted(TENANT_SERVICE_STATUSES))}")
    plan: str | None = None
    quotas: dict[str, Any] | None = None
    expires_at: datetime | None = None


def _to_response(view: TenantServiceView) -> TenantServiceResponse:
    return TenantServiceResponse(
        slug=view.slug,
        namespace=view.namespace,
        name=view.name,
        description=view.description,
        version=view.version,
        is_core=view.is_core,
        is_active=view.is_active,
        status=view.status,
        plan=view.plan,
        entitled=view.entitled,
        quotas=view.quotas,
        expires_at=view.expires_at,
    )


@router.get("/me", response_model=list[TenantServiceResponse])
@inject
async def my_services(
    actor: CurrentUser = Depends(get_current_user),
    uow_factory: Any = Depends(Provide[Container.unit_of_work]),
    catalog: ServiceCatalogService = Depends(Provide[Container.service_catalog]),
) -> list[TenantServiceResponse]:
    """What this tenant can use. Any authenticated user may read it."""
    async with uow_factory:
        views = await catalog.list_for_tenant(actor.tenant_id)
        return [_to_response(view) for view in views]


@router.get("", response_model=list[ServiceResponse])
@inject
async def list_services(
    _: CurrentUser = Depends(require_permission(PermissionCode.SERVICES_READ)),
    uow_factory: Any = Depends(Provide[Container.unit_of_work]),
    platform: PlatformServiceCatalog = Depends(Provide[Container.platform_service_catalog]),
) -> list[ServiceResponse]:
    """Every service the Hub knows about, contracted or not."""
    async with uow_factory:
        services = await platform.list_services()
        return [
            ServiceResponse(
                slug=service.slug,
                namespace=service.namespace,
                name=service.name,
                description=service.description,
                version=service.version,
                is_core=service.is_core,
                is_active=service.is_active,
            )
            for service in services
        ]


@router.get("/tenants/{tenant_id}", response_model=list[TenantServiceResponse])
@inject
async def tenant_services(
    tenant_id: UUID,
    _: CurrentUser = Depends(require_permission(PermissionCode.SERVICES_READ)),
    uow_factory: Any = Depends(Provide[Container.unit_of_work]),
    platform: PlatformServiceCatalog = Depends(Provide[Container.platform_service_catalog]),
) -> list[TenantServiceResponse]:
    async with uow_factory:
        views = await platform.list_for_tenant(tenant_id)
        return [_to_response(view) for view in views]


@router.put("/tenants/{tenant_id}/{slug}", response_model=TenantServiceResponse)
@inject
async def set_tenant_service(
    tenant_id: UUID,
    slug: str,
    body: SetTenantServiceRequest,
    _: CurrentUser = Depends(require_permission(PermissionCode.SERVICES_MANAGE)),
    uow_factory: Any = Depends(Provide[Container.unit_of_work]),
    platform: PlatformServiceCatalog = Depends(Provide[Container.platform_service_catalog]),
    entitlements: CatalogEntitlementProvider = Depends(
        Provide[Container.entitlement_provider]
    ),
) -> TenantServiceResponse:
    """Enable, suspend, re-plan or quota one service for one tenant."""
    async with uow_factory as uow:
        await platform.set_status(
            tenant_id=tenant_id,
            service_slug=slug,
            status=body.status,
            plan=body.plan,
            quotas=body.quotas,
            expires_at=body.expires_at,
        )
        await uow.commit()

    # The engine caches entitlements; a contract change must take effect now.
    entitlements.invalidate(tenant_id)

    async with uow_factory:
        views = await platform.list_for_tenant(tenant_id)
        return next(_to_response(view) for view in views if view.slug == slug)
