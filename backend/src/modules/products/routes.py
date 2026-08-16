# ruff: noqa: B008
"""Admin + product Hub routes."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, Field

from src.modules.authentication.services.token_service import TokenService
from src.modules.products.service import (
    BindingView,
    BindTenantBody,
    CreateInstanceRequest,
    HubGatewayService,
    ProductInstanceView,
    ProductRegistryService,
    TopologyView,
    UpdateInstanceRequest,
)
from src.shared.application.unit_of_work import UnitOfWork
from src.shared.infrastructure.di.container import Container
from src.shared.infrastructure.exceptions import UnauthorizedError
from src.shared.infrastructure.security.current_user import CurrentUser
from src.shared.infrastructure.security.dependencies import require_permission
from src.shared.infrastructure.security.permission_codes import PermissionCode
from src.shared.infrastructure.tenant_context import bind_rls_bypass, unbind_rls_bypass

admin_router = APIRouter(prefix="/products", tags=["products"])
hub_router = APIRouter(prefix="/hub", tags=["hub"])


@admin_router.get("/topology", response_model=TopologyView)
@inject
async def product_topology(
    _: CurrentUser = Depends(require_permission(PermissionCode.PRODUCTS_READ)),
    service: ProductRegistryService = Depends(Provide[Container.product_registry]),
    uow_factory: UnitOfWork = Depends(Provide[Container.unit_of_work]),
) -> TopologyView:
    token = bind_rls_bypass(True)
    try:
        async with uow_factory as uow:
            view = await service.topology()
            await uow.commit()
            return view
    finally:
        unbind_rls_bypass(token)


class TokenBody(BaseModel):
    client_id: str
    client_secret: str


class IntrospectBody(BaseModel):
    token: str


class AuthorizeBody(BaseModel):
    user_id: UUID
    tenant_id: UUID
    action: str
    resource_type: str | None = None
    resource_id: UUID | None = None


class EntitlementBody(BaseModel):
    tenant_id: UUID
    capability: str


class AuditBody(BaseModel):
    action: str
    user_id: UUID | None = None
    tenant_id: UUID | None = None
    resource_type: str | None = None
    resource_id: UUID | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EventBody(BaseModel):
    event_type: str
    tenant_id: UUID
    payload: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str | None = None


class HeartbeatBody(BaseModel):
    version: str
    status: str = "ok"


def _service_bearer(authorization: str | None) -> str:
    if not authorization:
        raise UnauthorizedError("Missing Authorization header")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise UnauthorizedError("Invalid Authorization header")
    return token.strip()


@admin_router.get("/instances", response_model=list[ProductInstanceView])
@inject
async def list_instances(
    _: CurrentUser = Depends(require_permission(PermissionCode.PRODUCTS_READ)),
    service: ProductRegistryService = Depends(Provide[Container.product_registry]),
    uow_factory: UnitOfWork = Depends(Provide[Container.unit_of_work]),
) -> list[ProductInstanceView]:
    token = bind_rls_bypass(True)
    try:
        async with uow_factory as uow:
            rows = await service.list_instances()
            await uow.commit()
            return rows
    finally:
        unbind_rls_bypass(token)


@admin_router.post("/instances", response_model=ProductInstanceView)
@inject
async def create_instance(
    body: CreateInstanceRequest,
    _: CurrentUser = Depends(require_permission(PermissionCode.PRODUCTS_MANAGE)),
    service: ProductRegistryService = Depends(Provide[Container.product_registry]),
    uow_factory: UnitOfWork = Depends(Provide[Container.unit_of_work]),
) -> ProductInstanceView:
    token = bind_rls_bypass(True)
    try:
        async with uow_factory as uow:
            row = await service.create(body)
            await uow.commit()
            return row
    finally:
        unbind_rls_bypass(token)


@admin_router.get("/instances/{instance_id}", response_model=ProductInstanceView)
@inject
async def get_instance(
    instance_id: UUID,
    _: CurrentUser = Depends(require_permission(PermissionCode.PRODUCTS_READ)),
    service: ProductRegistryService = Depends(Provide[Container.product_registry]),
    uow_factory: UnitOfWork = Depends(Provide[Container.unit_of_work]),
) -> ProductInstanceView:
    token = bind_rls_bypass(True)
    try:
        async with uow_factory as uow:
            row = await service.get(instance_id)
            await uow.commit()
            return row
    finally:
        unbind_rls_bypass(token)


@admin_router.patch("/instances/{instance_id}", response_model=ProductInstanceView)
@inject
async def update_instance(
    instance_id: UUID,
    body: UpdateInstanceRequest,
    _: CurrentUser = Depends(require_permission(PermissionCode.PRODUCTS_MANAGE)),
    service: ProductRegistryService = Depends(Provide[Container.product_registry]),
    uow_factory: UnitOfWork = Depends(Provide[Container.unit_of_work]),
) -> ProductInstanceView:
    token = bind_rls_bypass(True)
    try:
        async with uow_factory as uow:
            row = await service.update(instance_id, body)
            await uow.commit()
            return row
    finally:
        unbind_rls_bypass(token)


@admin_router.post("/instances/{instance_id}/deactivate")
@inject
async def deactivate_instance(
    instance_id: UUID,
    _: CurrentUser = Depends(require_permission(PermissionCode.PRODUCTS_MANAGE)),
    service: ProductRegistryService = Depends(Provide[Container.product_registry]),
    uow_factory: UnitOfWork = Depends(Provide[Container.unit_of_work]),
) -> dict[str, str]:
    token = bind_rls_bypass(True)
    try:
        async with uow_factory as uow:
            await service.deactivate(instance_id)
            await uow.commit()
            return {"status": "disabled"}
    finally:
        unbind_rls_bypass(token)


@admin_router.post("/instances/{instance_id}/probe")
@inject
async def probe_instance(
    instance_id: UUID,
    _: CurrentUser = Depends(require_permission(PermissionCode.PRODUCTS_MANAGE)),
    service: ProductRegistryService = Depends(Provide[Container.product_registry]),
    uow_factory: UnitOfWork = Depends(Provide[Container.unit_of_work]),
) -> dict[str, Any]:
    token = bind_rls_bypass(True)
    try:
        async with uow_factory as uow:
            result = await service.probe(instance_id)
            await uow.commit()
            return result
    finally:
        unbind_rls_bypass(token)


@admin_router.get("/instances/{instance_id}/bindings", response_model=list[BindingView])
@inject
async def list_bindings(
    instance_id: UUID,
    _: CurrentUser = Depends(require_permission(PermissionCode.PRODUCTS_READ)),
    service: ProductRegistryService = Depends(Provide[Container.product_registry]),
    uow_factory: UnitOfWork = Depends(Provide[Container.unit_of_work]),
) -> list[BindingView]:
    token = bind_rls_bypass(True)
    try:
        async with uow_factory as uow:
            rows = await service.list_bindings(instance_id)
            await uow.commit()
            return rows
    finally:
        unbind_rls_bypass(token)


@admin_router.put("/instances/{instance_id}/bindings", response_model=BindingView)
@inject
async def bind_tenant(
    instance_id: UUID,
    body: BindTenantBody,
    _: CurrentUser = Depends(require_permission(PermissionCode.PRODUCTS_MANAGE)),
    service: ProductRegistryService = Depends(Provide[Container.product_registry]),
    uow_factory: UnitOfWork = Depends(Provide[Container.unit_of_work]),
) -> BindingView:
    token = bind_rls_bypass(True)
    try:
        async with uow_factory as uow:
            row = await service.bind_tenant(instance_id, body)
            await uow.commit()
            return row
    finally:
        unbind_rls_bypass(token)


@hub_router.post("/token")
@inject
async def hub_token(
    body: TokenBody,
    service: HubGatewayService = Depends(Provide[Container.hub_gateway]),
    uow_factory: UnitOfWork = Depends(Provide[Container.unit_of_work]),
) -> dict[str, Any]:
    token = bind_rls_bypass(True)
    try:
        async with uow_factory as uow:
            result = await service.issue_token(body.client_id, body.client_secret)
            await uow.commit()
            return result
    finally:
        unbind_rls_bypass(token)


async def _require_instance(
    authorization: str | None,
    service: HubGatewayService,
) -> UUID:
    payload = service.decode_service_token(_service_bearer(authorization))
    return UUID(str(payload["sub"]))


@hub_router.post("/heartbeat")
@inject
async def heartbeat(
    body: HeartbeatBody,
    authorization: str | None = Header(default=None),
    service: HubGatewayService = Depends(Provide[Container.hub_gateway]),
    uow_factory: UnitOfWork = Depends(Provide[Container.unit_of_work]),
) -> dict[str, str]:
    token = bind_rls_bypass(True)
    try:
        async with uow_factory as uow:
            instance_id = await _require_instance(authorization, service)
            await service.heartbeat(instance_id, body.version, body.status)
            await uow.commit()
            return {"status": "ok"}
    finally:
        unbind_rls_bypass(token)


@hub_router.post("/introspect")
@inject
async def introspect(
    body: IntrospectBody,
    authorization: str | None = Header(default=None),
    service: HubGatewayService = Depends(Provide[Container.hub_gateway]),
    token_service: TokenService = Depends(Provide[Container.token_service]),
    uow_factory: UnitOfWork = Depends(Provide[Container.unit_of_work]),
) -> dict[str, Any]:
    token = bind_rls_bypass(True)
    try:
        async with uow_factory as uow:
            await _require_instance(authorization, service)
            result = await service.introspect_user_token(body.token, token_service)
            await uow.commit()
            return result
    finally:
        unbind_rls_bypass(token)


@hub_router.post("/authorize")
@inject
async def authorize(
    body: AuthorizeBody,
    authorization: str | None = Header(default=None),
    service: HubGatewayService = Depends(Provide[Container.hub_gateway]),
    uow_factory: UnitOfWork = Depends(Provide[Container.unit_of_work]),
) -> dict[str, Any]:
    token = bind_rls_bypass(True)
    try:
        async with uow_factory as uow:
            await _require_instance(authorization, service)
            result = await service.authorize(
                user_id=body.user_id, tenant_id=body.tenant_id, action=body.action
            )
            await uow.commit()
            return result
    finally:
        unbind_rls_bypass(token)


@hub_router.post("/entitlements/check")
@inject
async def check_entitlement(
    body: EntitlementBody,
    authorization: str | None = Header(default=None),
    service: HubGatewayService = Depends(Provide[Container.hub_gateway]),
    uow_factory: UnitOfWork = Depends(Provide[Container.unit_of_work]),
) -> dict[str, Any]:
    token = bind_rls_bypass(True)
    try:
        async with uow_factory as uow:
            await _require_instance(authorization, service)
            result = await service.check_entitlement(body.tenant_id, body.capability)
            await uow.commit()
            return result
    finally:
        unbind_rls_bypass(token)


@hub_router.post("/audit")
@inject
async def hub_audit(
    body: AuditBody,
    authorization: str | None = Header(default=None),
    service: HubGatewayService = Depends(Provide[Container.hub_gateway]),
    uow_factory: UnitOfWork = Depends(Provide[Container.unit_of_work]),
) -> dict[str, str]:
    token = bind_rls_bypass(True)
    try:
        async with uow_factory as uow:
            await _require_instance(authorization, service)
            await service.write_audit(body.model_dump())
            await uow.commit()
            return {"status": "ok"}
    finally:
        unbind_rls_bypass(token)


@hub_router.post("/events")
@inject
async def hub_events(
    body: EventBody,
    authorization: str | None = Header(default=None),
    service: HubGatewayService = Depends(Provide[Container.hub_gateway]),
    uow_factory: UnitOfWork = Depends(Provide[Container.unit_of_work]),
) -> dict[str, str]:
    token = bind_rls_bypass(True)
    try:
        async with uow_factory as uow:
            await _require_instance(authorization, service)
            await service.write_audit(
                {
                    "action": f"event.{body.event_type}",
                    "tenant_id": str(body.tenant_id),
                    "metadata": {
                        "payload": body.payload,
                        "correlation_id": body.correlation_id,
                    },
                }
            )
            await uow.commit()
            return {"status": "accepted"}
    finally:
        unbind_rls_bypass(token)


@hub_router.get("/tenants/{tenant_id}")
@inject
async def hub_tenant(
    tenant_id: UUID,
    authorization: str | None = Header(default=None),
    service: HubGatewayService = Depends(Provide[Container.hub_gateway]),
    uow_factory: UnitOfWork = Depends(Provide[Container.unit_of_work]),
) -> dict[str, Any]:
    token = bind_rls_bypass(True)
    try:
        async with uow_factory as uow:
            await _require_instance(authorization, service)
            result = await service.get_tenant(tenant_id)
            await uow.commit()
            return result
    finally:
        unbind_rls_bypass(token)
