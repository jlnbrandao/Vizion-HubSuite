"""Pydantic schemas for the billing HTTP surface."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ChargeLineResponse(BaseModel):
    kind: str
    label: str
    quantity: int
    unit_amount: Decimal
    amount: Decimal
    ref: str | None = None
    included: bool = False
    enabled: bool = True


class OverviewResponse(BaseModel):
    generated_at: datetime
    period_start: datetime
    period_end: datetime
    payment_due: datetime
    days_elapsed: int
    prepayments: Decimal
    discount: Decimal
    subtotal: Decimal
    total: Decimal
    users: list[ChargeLineResponse]
    services: list[ChargeLineResponse]
    promo_code: str | None = None


class InvoiceLineResponse(BaseModel):
    kind: str
    label: str
    quantity: int
    unit_amount: Decimal
    amount: Decimal
    ref: str | None = None


class InvoiceResponse(BaseModel):
    id: UUID
    period_start: datetime
    period_end: datetime
    status: str
    subtotal: Decimal
    discount: Decimal
    total: Decimal
    description: str
    invoice_url: str | None = None
    pix_payload: str | None = None
    created_at: datetime
    lines: list[InvoiceLineResponse] = Field(default_factory=list)


class PaymentMethodResponse(BaseModel):
    id: UUID
    billing_type: str
    brand: str
    last4: str
    holder_name: str
    is_primary: bool
    credit_card_token: str | None = None


class CreatePaymentMethodRequest(BaseModel):
    billing_type: str = "CREDIT_CARD"
    credit_card_token: str | None = None
    brand: str | None = None
    last4: str | None = None
    holder_name: str | None = None
    is_primary: bool = True
    card_number: str | None = None
    expiry_month: str | None = None
    expiry_year: str | None = None
    ccv: str | None = None


class BillingSettingsResponse(BaseModel):
    legal_name: str
    email: str
    cpf_cnpj: str
    postal_code: str
    address: str
    address_number: str
    complement: str
    province: str
    city: str
    state: str
    country: str
    cycle_close_day: int
    alert_enabled: bool
    promo_code: str | None = None
    asaas_linked: bool
    contracted_services: list[ChargeLineResponse] = Field(default_factory=list)


class UpdateBillingSettingsRequest(BaseModel):
    legal_name: str | None = None
    email: str | None = None
    cpf_cnpj: str | None = None
    postal_code: str | None = None
    address: str | None = None
    address_number: str | None = None
    complement: str | None = None
    province: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    cycle_close_day: int | None = None
    alert_enabled: bool | None = None


class ApplyPromoRequest(BaseModel):
    code: str


class CreatePaymentRequest(BaseModel):
    billing_type: str = "PIX"
    payment_method_id: UUID | None = None
    amount: Decimal | None = None


class CreatePaymentResponse(BaseModel):
    invoice: InvoiceResponse
    invoice_url: str | None = None
    pix_payload: str | None = None


class AsaasWebhookRequest(BaseModel):
    event: str | None = None
    payment: dict[str, Any] | None = None
