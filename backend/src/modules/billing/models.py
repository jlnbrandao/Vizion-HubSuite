"""Tenant-scoped billing tables. Every row carries `tenant_id` and is RLS-forced."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.infrastructure.database import Base

INVOICE_STATUSES = frozenset({"draft", "pending", "paid", "overdue", "cancelled"})
LINE_KINDS = frozenset({"user", "service", "discount"})
CYCLE_CLOSE_DAYS = frozenset({3, 6, 9})


class BillingCustomerModel(Base):
    __tablename__ = "billing_customers"
    __table_args__ = (UniqueConstraint("tenant_id", name="uq_billing_customers_tenant"),)

    id: Mapped[UUID] = mapped_column(postgresql.UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    asaas_customer_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    legal_name: Mapped[str] = mapped_column(String(150), nullable=False, default="")
    email: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    cpf_cnpj: Mapped[str] = mapped_column(String(18), nullable=False, default="")
    postal_code: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    address: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    address_number: Mapped[str] = mapped_column(String(20), nullable=False, default="")
    complement: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    province: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    city: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    state: Mapped[str] = mapped_column(String(2), nullable=False, default="")
    country: Mapped[str] = mapped_column(String(80), nullable=False, default="Brasil")
    cycle_close_day: Mapped[int] = mapped_column(Integer, nullable=False, default=9)
    alert_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    promo_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class BillingPaymentMethodModel(Base):
    __tablename__ = "billing_payment_methods"

    id: Mapped[UUID] = mapped_column(postgresql.UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    asaas_token: Mapped[str | None] = mapped_column(String(128), nullable=True)
    billing_type: Mapped[str] = mapped_column(String(24), nullable=False, default="CREDIT_CARD")
    brand: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    last4: Mapped[str] = mapped_column(String(4), nullable=False, default="")
    holder_name: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class BillingInvoiceModel(Base):
    __tablename__ = "billing_invoices"

    id: Mapped[UUID] = mapped_column(postgresql.UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    discount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    total: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    asaas_payment_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    invoice_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    pix_payload: Mapped[str | None] = mapped_column(String(512), nullable=True)
    description: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class BillingInvoiceLineModel(Base):
    __tablename__ = "billing_invoice_lines"

    id: Mapped[UUID] = mapped_column(postgresql.UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    invoice_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("billing_invoices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    label: Mapped[str] = mapped_column(String(160), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    unit_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    ref: Mapped[str | None] = mapped_column(String(64), nullable=True)
