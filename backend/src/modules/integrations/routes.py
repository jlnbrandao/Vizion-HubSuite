"""HTTP routes for the Integration Hub."""

# ruff: noqa: B008

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Query, Request, status

from src.modules.integrations.schemas import (
    CreateIntegrationRequest,
    IntegrationLogResponse,
    IntegrationResponse,
    IntegrationStatusResponse,
    IntegrationSyncResponse,
    IntegrationTestResponse,
    UpdateIntegrationRequest,
    WebhookReceiveResponse,
)
from src.modules.integrations.service import IntegrationService
from src.modules.services.quotas import ServiceQuotaGuard
from src.shared.application.unit_of_work import UnitOfWork
from src.shared.infrastructure.di.container import Container
from src.shared.infrastructure.exceptions import ValidationError
from src.shared.infrastructure.security.current_user import CurrentUser
from src.shared.infrastructure.security.dependencies import require_permission
from src.shared.infrastructure.security.permission_codes import (
    SERVICE_INTEGRATION,
    PermissionCode,
)

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.get("", response_model=list[IntegrationResponse])
@inject
async def list_integrations(
    _: CurrentUser = Depends(require_permission(PermissionCode.INTEGRATION_READ)),
    service: IntegrationService = Depends(Provide[Container.integration_service]),
    uow_factory: UnitOfWork = Depends(Provide[Container.unit_of_work]),
) -> list[IntegrationResponse]:
    async with uow_factory as uow:
        rows = await service.list()
        await uow.commit()
        return rows


@router.get("/{integration_id}", response_model=IntegrationResponse)
@inject
async def get_integration(
    integration_id: UUID,
    _: CurrentUser = Depends(require_permission(PermissionCode.INTEGRATION_READ)),
    service: IntegrationService = Depends(Provide[Container.integration_service]),
    uow_factory: UnitOfWork = Depends(Provide[Container.unit_of_work]),
) -> IntegrationResponse:
    async with uow_factory as uow:
        row = await service.get(integration_id)
        await uow.commit()
        return row


@router.post("", response_model=IntegrationResponse, status_code=status.HTTP_201_CREATED)
@inject
async def create_integration(
    body: CreateIntegrationRequest,
    _: CurrentUser = Depends(require_permission(PermissionCode.INTEGRATION_CREATE)),
    service: IntegrationService = Depends(Provide[Container.integration_service]),
    uow_factory: UnitOfWork = Depends(Provide[Container.unit_of_work]),
) -> IntegrationResponse:
    async with uow_factory as uow:
        row = await service.create(body)
        await uow.commit()
        return row


@router.put("/{integration_id}", response_model=IntegrationResponse)
@inject
async def update_integration(
    integration_id: UUID,
    body: UpdateIntegrationRequest,
    _: CurrentUser = Depends(require_permission(PermissionCode.INTEGRATION_UPDATE)),
    service: IntegrationService = Depends(Provide[Container.integration_service]),
    uow_factory: UnitOfWork = Depends(Provide[Container.unit_of_work]),
) -> IntegrationResponse:
    async with uow_factory as uow:
        row = await service.update(integration_id, body)
        await uow.commit()
        return row


@router.delete("/{integration_id}", status_code=status.HTTP_204_NO_CONTENT)
@inject
async def delete_integration(
    integration_id: UUID,
    _: CurrentUser = Depends(require_permission(PermissionCode.INTEGRATION_DELETE)),
    service: IntegrationService = Depends(Provide[Container.integration_service]),
    uow_factory: UnitOfWork = Depends(Provide[Container.unit_of_work]),
) -> None:
    async with uow_factory as uow:
        await service.delete(integration_id)
        await uow.commit()


@router.post(
    "/{integration_id}/webhook/events",
    response_model=WebhookReceiveResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
@inject
async def receive_webhook_event(
    integration_id: UUID,
    request: Request,
    service: IntegrationService = Depends(Provide[Container.integration_service]),
    uow_factory: UnitOfWork = Depends(Provide[Container.unit_of_work]),
) -> WebhookReceiveResponse:
    """Inbound webhook from third parties — HMAC auth, no JWT.

    The third party must call the tenant Host (e.g. ows.localhost) so RLS
    resolves the correct tenant. Sign the raw body with HMAC-SHA256.
    """
    raw_body = await request.body()
    try:
        payload: dict[str, Any] = json.loads(raw_body.decode("utf-8") or "{}")
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValidationError("Webhook body must be JSON") from exc
    if not isinstance(payload, dict):
        raise ValidationError("Webhook body must be a JSON object")

    headers = {key.lower(): value for key, value in request.headers.items()}

    async with uow_factory as uow:
        result = await service.receive_webhook(
            integration_id,
            raw_body=raw_body,
            headers=headers,
            payload=payload,
        )
        await uow.commit()
        return result


@router.post("/{integration_id}/test", response_model=IntegrationTestResponse)
@inject
async def test_integration(
    integration_id: UUID,
    _: CurrentUser = Depends(require_permission(PermissionCode.INTEGRATION_TEST)),
    service: IntegrationService = Depends(Provide[Container.integration_service]),
    uow_factory: UnitOfWork = Depends(Provide[Container.unit_of_work]),
) -> IntegrationTestResponse:
    async with uow_factory as uow:
        result = await service.test(integration_id)
        await uow.commit()
        return result


@router.post("/{integration_id}/sync", response_model=IntegrationSyncResponse)
@inject
async def sync_integration(
    integration_id: UUID,
    actor: CurrentUser = Depends(require_permission(PermissionCode.INTEGRATION_SYNC)),
    service: IntegrationService = Depends(Provide[Container.integration_service]),
    uow_factory: UnitOfWork = Depends(Provide[Container.unit_of_work]),
    quotas: ServiceQuotaGuard = Depends(Provide[Container.service_quota_guard]),
) -> IntegrationSyncResponse:
    # Metered operation: the tenant's plan decides how often it may run.
    await quotas.enforce(
        tenant_id=actor.tenant_id,
        namespace=SERVICE_INTEGRATION,
        metric="sync_per_hour",
        window_seconds=3600,
    )
    async with uow_factory as uow:
        result = await service.sync(integration_id)
        await uow.commit()
        return result


@router.get("/{integration_id}/status", response_model=IntegrationStatusResponse)
@inject
async def integration_status(
    integration_id: UUID,
    _: CurrentUser = Depends(require_permission(PermissionCode.INTEGRATION_READ)),
    service: IntegrationService = Depends(Provide[Container.integration_service]),
    uow_factory: UnitOfWork = Depends(Provide[Container.unit_of_work]),
) -> IntegrationStatusResponse:
    async with uow_factory as uow:
        result = await service.get_status(integration_id)
        await uow.commit()
        return result


@router.get("/{integration_id}/logs", response_model=list[IntegrationLogResponse])
@inject
async def integration_logs(
    integration_id: UUID,
    limit: int = Query(default=50, ge=1, le=200),
    _: CurrentUser = Depends(require_permission(PermissionCode.INTEGRATION_LOGS_READ)),
    service: IntegrationService = Depends(Provide[Container.integration_service]),
    uow_factory: UnitOfWork = Depends(Provide[Container.unit_of_work]),
) -> list[IntegrationLogResponse]:
    async with uow_factory as uow:
        rows = await service.list_logs(integration_id, limit=limit)
        await uow.commit()
        return rows
