"""HTTP routes for the Billing service slice."""

# ruff: noqa: B008

from __future__ import annotations

from uuid import UUID

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import Response

from src.modules.billing.schemas import (
    ApplyPromoRequest,
    AsaasWebhookRequest,
    BillingSettingsResponse,
    CreatePaymentMethodRequest,
    CreatePaymentRequest,
    CreatePaymentResponse,
    InvoiceResponse,
    OverviewResponse,
    PaymentMethodResponse,
    UpdateBillingSettingsRequest,
)
from src.modules.billing.service import BillingService
from src.shared.application.unit_of_work import UnitOfWork
from src.shared.infrastructure.di.container import Container
from src.shared.infrastructure.security.current_user import CurrentUser
from src.shared.infrastructure.security.dependencies import require_permission
from src.shared.infrastructure.security.permission_codes import PermissionCode
from src.shared.infrastructure.tenant_context import bind_rls_bypass, unbind_rls_bypass

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/overview", response_model=OverviewResponse)
@inject
async def get_overview(
    actor: CurrentUser = Depends(require_permission(PermissionCode.INVOICES_READ)),
    service: BillingService = Depends(Provide[Container.billing_service]),
    uow_factory: UnitOfWork = Depends(Provide[Container.unit_of_work]),
) -> OverviewResponse:
    async with uow_factory as uow:
        view = await service.overview(actor_id=actor.id)
        await uow.commit()
        return view


@router.get("/invoices", response_model=list[InvoiceResponse])
@inject
async def list_invoices(
    _: CurrentUser = Depends(require_permission(PermissionCode.INVOICES_READ)),
    service: BillingService = Depends(Provide[Container.billing_service]),
    uow_factory: UnitOfWork = Depends(Provide[Container.unit_of_work]),
) -> list[InvoiceResponse]:
    async with uow_factory:
        return await service.list_invoices()


@router.get("/invoices/{invoice_id}/export")
@inject
async def export_invoice(
    invoice_id: UUID,
    _: CurrentUser = Depends(require_permission(PermissionCode.INVOICES_EXPORT)),
    service: BillingService = Depends(Provide[Container.billing_service]),
    uow_factory: UnitOfWork = Depends(Provide[Container.unit_of_work]),
) -> Response:
    async with uow_factory:
        filename, content = await service.export_invoice(invoice_id)
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/payments", response_model=CreatePaymentResponse)
@inject
async def create_payment(
    body: CreatePaymentRequest,
    actor: CurrentUser = Depends(require_permission(PermissionCode.PAYMENTS_CREATE)),
    service: BillingService = Depends(Provide[Container.billing_service]),
    uow_factory: UnitOfWork = Depends(Provide[Container.unit_of_work]),
) -> CreatePaymentResponse:
    async with uow_factory as uow:
        result = await service.create_payment(body, actor_id=actor.id)
        await uow.commit()
        return result


@router.get("/payment-methods", response_model=list[PaymentMethodResponse])
@inject
async def list_payment_methods(
    _: CurrentUser = Depends(require_permission(PermissionCode.PAYMENT_METHODS_READ)),
    service: BillingService = Depends(Provide[Container.billing_service]),
    uow_factory: UnitOfWork = Depends(Provide[Container.unit_of_work]),
) -> list[PaymentMethodResponse]:
    async with uow_factory:
        return await service.list_payment_methods()


@router.post("/payment-methods", response_model=PaymentMethodResponse)
@inject
async def add_payment_method(
    body: CreatePaymentMethodRequest,
    actor: CurrentUser = Depends(require_permission(PermissionCode.PAYMENT_METHODS_MANAGE)),
    service: BillingService = Depends(Provide[Container.billing_service]),
    uow_factory: UnitOfWork = Depends(Provide[Container.unit_of_work]),
) -> PaymentMethodResponse:
    async with uow_factory as uow:
        result = await service.add_payment_method(body, actor_id=actor.id)
        await uow.commit()
        return result


@router.get("/settings", response_model=BillingSettingsResponse)
@inject
async def get_settings(
    _: CurrentUser = Depends(require_permission(PermissionCode.BILLING_SETTINGS_READ)),
    service: BillingService = Depends(Provide[Container.billing_service]),
    uow_factory: UnitOfWork = Depends(Provide[Container.unit_of_work]),
) -> BillingSettingsResponse:
    async with uow_factory as uow:
        result = await service.get_settings()
        await uow.commit()
        return result


@router.put("/settings", response_model=BillingSettingsResponse)
@inject
async def update_settings(
    body: UpdateBillingSettingsRequest,
    actor: CurrentUser = Depends(require_permission(PermissionCode.BILLING_SETTINGS_UPDATE)),
    service: BillingService = Depends(Provide[Container.billing_service]),
    uow_factory: UnitOfWork = Depends(Provide[Container.unit_of_work]),
) -> BillingSettingsResponse:
    async with uow_factory as uow:
        result = await service.update_settings(body, actor_id=actor.id)
        await uow.commit()
        return result


@router.post("/promos", response_model=BillingSettingsResponse)
@inject
async def apply_promo(
    body: ApplyPromoRequest,
    actor: CurrentUser = Depends(require_permission(PermissionCode.BILLING_SETTINGS_UPDATE)),
    service: BillingService = Depends(Provide[Container.billing_service]),
    uow_factory: UnitOfWork = Depends(Provide[Container.unit_of_work]),
) -> BillingSettingsResponse:
    async with uow_factory as uow:
        result = await service.apply_promo(body, actor_id=actor.id)
        await uow.commit()
        return result


@router.post("/webhooks/asaas")
@inject
async def asaas_webhook(
    request: Request,
    body: AsaasWebhookRequest,
    service: BillingService = Depends(Provide[Container.billing_service]),
    uow_factory: UnitOfWork = Depends(Provide[Container.unit_of_work]),
    asaas_access_token: str | None = Header(default=None, alias="asaas-access-token"),
) -> dict[str, str]:
    token = asaas_access_token or request.headers.get("asaas-access-token")
    bypass = bind_rls_bypass(True)
    try:
        async with uow_factory as uow:
            await service.handle_webhook(body.model_dump(), token=token)
            await uow.commit()
    finally:
        unbind_rls_bypass(bypass)
    return {"status": "ok"}
