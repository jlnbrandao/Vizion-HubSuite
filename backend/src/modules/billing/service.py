"""Billing application service: estimates, invoices, Asaas and settings."""

from __future__ import annotations

from calendar import monthrange
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import select

from src.config.settings import Settings
from src.modules.billing.asaas import AsaasClient, map_asaas_status, money
from src.modules.billing.models import (
    CYCLE_CLOSE_DAYS,
    BillingCustomerModel,
    BillingInvoiceLineModel,
    BillingInvoiceModel,
    BillingPaymentMethodModel,
)
from src.modules.billing.pricing import (
    USER_MONTHLY_BRL,
    is_included_service,
    normalize_promo,
    promo_discount,
    service_monthly_price,
)
from src.modules.billing.schemas import (
    ApplyPromoRequest,
    BillingSettingsResponse,
    ChargeLineResponse,
    CreatePaymentMethodRequest,
    CreatePaymentRequest,
    CreatePaymentResponse,
    InvoiceLineResponse,
    InvoiceResponse,
    OverviewResponse,
    PaymentMethodResponse,
    UpdateBillingSettingsRequest,
)
from src.modules.iam.audit.service import AuditService
from src.modules.services.models import ENTITLED_STATUSES
from src.modules.services.service import ServiceCatalogService
from src.modules.tenants.repositories.tenant_model import TenantModel
from src.modules.users.repositories.user_model import UserModel
from src.shared.infrastructure.exceptions import NotFoundError, ValidationError
from src.shared.infrastructure.session_context import get_current_session
from src.shared.infrastructure.tenant_context import require_current_tenant_id


def current_period(now: datetime, close_day: int) -> tuple[datetime, datetime]:
    """Billing window that ends on the next cycle-close day (UTC)."""
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    start_year, start_month = now.year, now.month
    if now.day < close_day:
        if start_month == 1:
            start_year -= 1
            start_month = 12
        else:
            start_month -= 1
    start_day = min(close_day, monthrange(start_year, start_month)[1])
    start = datetime(start_year, start_month, start_day, tzinfo=UTC)
    if start_month == 12:
        end_year, end_month = start_year + 1, 1
    else:
        end_year, end_month = start_year, start_month + 1
    end_day = min(close_day, monthrange(end_year, end_month)[1])
    end = datetime(end_year, end_month, end_day, tzinfo=UTC)
    return start, end


class BillingService:
    def __init__(
        self,
        settings: Settings,
        asaas: AsaasClient,
        catalog: ServiceCatalogService,
        audit: AuditService,
    ) -> None:
        self._settings = settings
        self._asaas = asaas
        self._catalog = catalog
        self._audit = audit

    async def overview(self, *, actor_id: UUID) -> OverviewResponse:
        tenant_id = require_current_tenant_id()
        customer = await self._get_or_create_customer(tenant_id)
        now = datetime.now(UTC)
        period_start, period_end = current_period(now, customer.cycle_close_day)
        users, services, discount = await self._charge_lines(tenant_id, customer.promo_code)
        subtotal = sum((line.amount for line in (*users, *services)), Decimal("0.00"))
        total = max(Decimal("0.00"), subtotal - discount)
        return OverviewResponse(
            generated_at=now,
            period_start=period_start,
            period_end=period_end,
            payment_due=period_end,
            days_elapsed=max(0, (now.date() - period_start.date()).days),
            prepayments=Decimal("0.00"),
            discount=discount,
            subtotal=subtotal,
            total=total,
            users=users,
            services=services,
            promo_code=customer.promo_code,
        )

    async def list_invoices(self) -> list[InvoiceResponse]:
        tenant_id = require_current_tenant_id()
        session = get_current_session()
        result = await session.execute(
            select(BillingInvoiceModel)
            .where(BillingInvoiceModel.tenant_id == tenant_id)
            .order_by(BillingInvoiceModel.period_end.desc())
        )
        invoices = list(result.scalars().all())
        return [await self._invoice_response(invoice, include_lines=False) for invoice in invoices]

    async def export_invoice(self, invoice_id: UUID) -> tuple[str, str]:
        invoice = await self._require_invoice(invoice_id)
        response = await self._invoice_response(invoice, include_lines=True)
        rows = [
            "kind,label,quantity,unit_amount,amount",
            *[
                f"{line.kind},{line.label},{line.quantity},{line.unit_amount},{line.amount}"
                for line in response.lines
            ],
            f"total,Total,1,{response.total},{response.total}",
        ]
        filename = f"invoice-{invoice.id}.csv"
        return filename, "\n".join(rows) + "\n"

    async def get_settings(self) -> BillingSettingsResponse:
        tenant_id = require_current_tenant_id()
        customer = await self._get_or_create_customer(tenant_id)
        _, services, _ = await self._charge_lines(tenant_id, customer.promo_code)
        return self._settings_response(customer, services)

    async def update_settings(
        self, body: UpdateBillingSettingsRequest, *, actor_id: UUID
    ) -> BillingSettingsResponse:
        tenant_id = require_current_tenant_id()
        customer = await self._get_or_create_customer(tenant_id)
        data = body.model_dump(exclude_unset=True)
        if "cycle_close_day" in data and data["cycle_close_day"] not in CYCLE_CLOSE_DAYS:
            raise ValidationError("cycle_close_day must be 3, 6 or 9")
        for field, value in data.items():
            setattr(customer, field, value if value is not None else getattr(customer, field))
        await self._sync_asaas_customer(customer)
        await get_current_session().flush()
        await self._audit.persist(
            action="billing.settings.update",
            actor_user_id=actor_id,
            actor_type="user",
            resource_type="billing_settings",
            resource_id=str(customer.id),
        )
        _, services, _ = await self._charge_lines(tenant_id, customer.promo_code)
        return self._settings_response(customer, services)

    async def apply_promo(
        self, body: ApplyPromoRequest, *, actor_id: UUID
    ) -> BillingSettingsResponse:
        code = normalize_promo(body.code)
        if code is None:
            raise ValidationError("Unknown promo code")
        tenant_id = require_current_tenant_id()
        customer = await self._get_or_create_customer(tenant_id)
        customer.promo_code = code
        await get_current_session().flush()
        await self._audit.persist(
            action="billing.promo.apply",
            actor_user_id=actor_id,
            actor_type="user",
            resource_type="billing_settings",
            resource_id=str(customer.id),
            payload={"code": code},
        )
        _, services, _ = await self._charge_lines(tenant_id, customer.promo_code)
        return self._settings_response(customer, services)

    async def list_payment_methods(self) -> list[PaymentMethodResponse]:
        tenant_id = require_current_tenant_id()
        session = get_current_session()
        result = await session.execute(
            select(BillingPaymentMethodModel)
            .where(BillingPaymentMethodModel.tenant_id == tenant_id)
            .order_by(BillingPaymentMethodModel.created_at.desc())
        )
        return [self._method_response(row) for row in result.scalars().all()]

    async def add_payment_method(
        self, body: CreatePaymentMethodRequest, *, actor_id: UUID
    ) -> PaymentMethodResponse:
        tenant_id = require_current_tenant_id()
        customer = await self._get_or_create_customer(tenant_id)
        token = (body.credit_card_token or "").strip() or None
        brand = (body.brand or "").strip()
        last4 = (body.last4 or "").strip()
        holder = (body.holder_name or "").strip()

        if body.card_number and self._asaas.configured:
            await self._ensure_asaas_customer(customer)
            tokenized = await self._asaas.tokenize_card(
                {
                    "customer": customer.asaas_customer_id,
                    "creditCard": {
                        "holderName": holder or customer.legal_name,
                        "number": body.card_number,
                        "expiryMonth": body.expiry_month,
                        "expiryYear": body.expiry_year,
                        "ccv": body.ccv,
                    },
                }
            )
            token = str(tokenized.get("creditCardToken") or token or "")
            card = tokenized.get("creditCard") or {}
            brand = str(card.get("creditCardBrand") or brand)
            last4 = str(card.get("creditCardNumber") or last4)[-4:]

        session = get_current_session()
        if body.is_primary:
            existing = await session.execute(
                select(BillingPaymentMethodModel).where(
                    BillingPaymentMethodModel.tenant_id == tenant_id
                )
            )
            for row in existing.scalars().all():
                row.is_primary = False

        model = BillingPaymentMethodModel(
            id=uuid4(),
            tenant_id=tenant_id,
            asaas_token=token,
            billing_type=body.billing_type.strip().upper() or "CREDIT_CARD",
            brand=brand,
            last4=last4[-4:] if last4 else "",
            holder_name=holder,
            is_primary=body.is_primary,
        )
        session.add(model)
        await session.flush()
        await self._audit.persist(
            action="billing.payment_methods.create",
            actor_user_id=actor_id,
            actor_type="user",
            resource_type="payment_methods",
            resource_id=str(model.id),
        )
        return self._method_response(model)

    async def create_payment(
        self, body: CreatePaymentRequest, *, actor_id: UUID
    ) -> CreatePaymentResponse:
        tenant_id = require_current_tenant_id()
        customer = await self._get_or_create_customer(tenant_id)
        now = datetime.now(UTC)
        period_start, period_end = current_period(now, customer.cycle_close_day)
        users, services, discount = await self._charge_lines(tenant_id, customer.promo_code)
        subtotal = sum((line.amount for line in (*users, *services)), Decimal("0.00"))
        estimated = max(Decimal("0.00"), subtotal - discount)
        amount = body.amount if body.amount is not None else estimated
        if amount <= 0:
            raise ValidationError("Payment amount must be greater than zero")

        billing_type = body.billing_type.strip().upper() or "PIX"
        token: str | None = None
        if body.payment_method_id is not None:
            method = await self._require_method(body.payment_method_id)
            token = method.asaas_token
            billing_type = method.billing_type

        invoice = BillingInvoiceModel(
            id=uuid4(),
            tenant_id=tenant_id,
            period_start=period_start,
            period_end=period_end,
            status="pending",
            subtotal=subtotal,
            discount=discount,
            total=amount,
            description=f"Fatura {period_start:%b/%Y}",
        )
        session = get_current_session()
        session.add(invoice)
        for line in (*users, *services):
            session.add(
                BillingInvoiceLineModel(
                    id=uuid4(),
                    tenant_id=tenant_id,
                    invoice_id=invoice.id,
                    kind=line.kind,
                    label=line.label,
                    quantity=line.quantity,
                    unit_amount=line.unit_amount,
                    amount=line.amount,
                    ref=line.ref,
                )
            )
        if discount > 0:
            session.add(
                BillingInvoiceLineModel(
                    id=uuid4(),
                    tenant_id=tenant_id,
                    invoice_id=invoice.id,
                    kind="discount",
                    label=f"Promo {customer.promo_code}",
                    quantity=1,
                    unit_amount=discount,
                    amount=discount,
                    ref=customer.promo_code,
                )
            )

        if self._asaas.configured:
            await self._ensure_asaas_customer(customer)
            payload: dict = {
                "customer": customer.asaas_customer_id,
                "billingType": billing_type,
                "value": money(amount),
                "dueDate": period_end.date().isoformat(),
                "description": invoice.description,
                "externalReference": str(invoice.id),
            }
            if token and billing_type == "CREDIT_CARD":
                payload["creditCardToken"] = token
            created = await self._asaas.create_payment(payload)
            invoice.asaas_payment_id = str(created.get("id") or "") or None
            invoice.invoice_url = created.get("invoiceUrl") or created.get("bankSlipUrl")
            invoice.pix_payload = created.get("payload") or created.get("encodedImage")
            invoice.status = map_asaas_status(created.get("status"))

        await session.flush()
        await self._audit.persist(
            action="billing.payments.create",
            actor_user_id=actor_id,
            actor_type="user",
            resource_type="invoices",
            resource_id=str(invoice.id),
            payload={"amount": str(amount), "billing_type": billing_type},
        )
        response = await self._invoice_response(invoice, include_lines=True)
        return CreatePaymentResponse(
            invoice=response,
            invoice_url=invoice.invoice_url,
            pix_payload=invoice.pix_payload,
        )

    async def handle_webhook(self, payload: dict, *, token: str | None) -> None:
        self._asaas.verify_webhook(token)
        payment = payload.get("payment") if isinstance(payload.get("payment"), dict) else {}
        asaas_id = str(payment.get("id") or "")
        customer_id = str(payment.get("customer") or "")
        if not asaas_id:
            raise ValidationError("Webhook payment id is missing")

        session = get_current_session()
        invoice: BillingInvoiceModel | None = None
        result = await session.execute(
            select(BillingInvoiceModel).where(BillingInvoiceModel.asaas_payment_id == asaas_id)
        )
        invoice = result.scalar_one_or_none()
        if invoice is None and customer_id:
            result = await session.execute(
                select(BillingInvoiceModel)
                .join(
                    BillingCustomerModel,
                    BillingCustomerModel.tenant_id == BillingInvoiceModel.tenant_id,
                )
                .where(
                    BillingCustomerModel.asaas_customer_id == customer_id,
                    BillingInvoiceModel.status == "pending",
                )
                .order_by(BillingInvoiceModel.created_at.desc())
                .limit(1)
            )
            invoice = result.scalar_one_or_none()
        if invoice is None:
            return
        invoice.status = map_asaas_status(str(payment.get("status") or ""))
        invoice.invoice_url = payment.get("invoiceUrl") or invoice.invoice_url
        await session.flush()
        await self._audit.persist(
            action="billing.webhook.update",
            actor_type="system",
            resource_type="invoices",
            resource_id=str(invoice.id),
            tenant_id=invoice.tenant_id,
            payload={"asaas_status": payment.get("status"), "event": payload.get("event")},
        )

    async def _charge_lines(
        self, tenant_id: UUID, promo_code: str | None
    ) -> tuple[list[ChargeLineResponse], list[ChargeLineResponse], Decimal]:
        session = get_current_session()
        users_result = await session.execute(
            select(UserModel.id, UserModel.full_name, UserModel.email, UserModel.is_active).where(
                UserModel.tenant_id == tenant_id
            )
        )
        user_lines: list[ChargeLineResponse] = []
        for user_id, full_name, email, is_active in users_result.all():
            if not is_active:
                continue
            user_lines.append(
                ChargeLineResponse(
                    kind="user",
                    label=full_name or email,
                    quantity=1,
                    unit_amount=USER_MONTHLY_BRL,
                    amount=USER_MONTHLY_BRL,
                    ref=str(user_id),
                    enabled=True,
                )
            )

        views = await self._catalog.list_for_tenant(tenant_id)
        service_lines: list[ChargeLineResponse] = []
        for view in views:
            entitled = view.status in ENTITLED_STATUSES if view.status else False
            included = is_included_service(view.slug)
            unit = (
                Decimal("0.00")
                if included
                else service_monthly_price(view.slug, view.plan or "standard")
            )
            amount = unit if entitled and not included else Decimal("0.00")
            service_lines.append(
                ChargeLineResponse(
                    kind="service",
                    label=view.name,
                    quantity=1,
                    unit_amount=unit,
                    amount=amount,
                    ref=view.slug,
                    included=included,
                    enabled=entitled,
                )
            )

        discount = promo_discount(promo_code)
        return user_lines, service_lines, discount

    async def _get_or_create_customer(self, tenant_id: UUID) -> BillingCustomerModel:
        session = get_current_session()
        result = await session.execute(
            select(BillingCustomerModel).where(BillingCustomerModel.tenant_id == tenant_id)
        )
        customer = result.scalar_one_or_none()
        if customer is not None:
            return customer
        tenant = await session.get(TenantModel, tenant_id)
        customer = BillingCustomerModel(
            id=uuid4(),
            tenant_id=tenant_id,
            legal_name=tenant.name if tenant is not None else "",
        )
        session.add(customer)
        await session.flush()
        return customer

    async def _ensure_asaas_customer(self, customer: BillingCustomerModel) -> None:
        if not self._asaas.configured:
            return
        payload = {
            "name": customer.legal_name or "Tenant",
            "email": customer.email or None,
            "cpfCnpj": customer.cpf_cnpj or None,
            "postalCode": customer.postal_code or None,
            "address": customer.address or None,
            "addressNumber": customer.address_number or None,
            "complement": customer.complement or None,
            "province": customer.province or None,
            "city": customer.city or None,
            "state": customer.state or None,
        }
        payload = {key: value for key, value in payload.items() if value}
        if customer.asaas_customer_id:
            await self._asaas.update_customer(customer.asaas_customer_id, payload)
            return
        created = await self._asaas.create_customer(payload)
        customer.asaas_customer_id = str(created.get("id") or "") or None
        await get_current_session().flush()

    async def _sync_asaas_customer(self, customer: BillingCustomerModel) -> None:
        if self._asaas.configured and (customer.legal_name or customer.email or customer.cpf_cnpj):
            await self._ensure_asaas_customer(customer)

    async def _require_invoice(self, invoice_id: UUID) -> BillingInvoiceModel:
        tenant_id = require_current_tenant_id()
        result = await get_current_session().execute(
            select(BillingInvoiceModel).where(
                BillingInvoiceModel.id == invoice_id,
                BillingInvoiceModel.tenant_id == tenant_id,
            )
        )
        invoice = result.scalar_one_or_none()
        if invoice is None:
            raise NotFoundError("Invoice not found")
        return invoice

    async def _require_method(self, method_id: UUID) -> BillingPaymentMethodModel:
        tenant_id = require_current_tenant_id()
        result = await get_current_session().execute(
            select(BillingPaymentMethodModel).where(
                BillingPaymentMethodModel.id == method_id,
                BillingPaymentMethodModel.tenant_id == tenant_id,
            )
        )
        method = result.scalar_one_or_none()
        if method is None:
            raise NotFoundError("Payment method not found")
        return method

    async def _invoice_response(
        self, invoice: BillingInvoiceModel, *, include_lines: bool
    ) -> InvoiceResponse:
        lines: list[InvoiceLineResponse] = []
        if include_lines:
            result = await get_current_session().execute(
                select(BillingInvoiceLineModel)
                .where(BillingInvoiceLineModel.invoice_id == invoice.id)
                .order_by(BillingInvoiceLineModel.kind)
            )
            lines = [
                InvoiceLineResponse(
                    kind=row.kind,
                    label=row.label,
                    quantity=row.quantity,
                    unit_amount=row.unit_amount,
                    amount=row.amount,
                    ref=row.ref,
                )
                for row in result.scalars().all()
            ]
        return InvoiceResponse(
            id=invoice.id,
            period_start=invoice.period_start,
            period_end=invoice.period_end,
            status=invoice.status,
            subtotal=invoice.subtotal,
            discount=invoice.discount,
            total=invoice.total,
            description=invoice.description,
            invoice_url=invoice.invoice_url,
            pix_payload=invoice.pix_payload,
            created_at=invoice.created_at,
            lines=lines,
        )

    def _settings_response(
        self, customer: BillingCustomerModel, services: list[ChargeLineResponse]
    ) -> BillingSettingsResponse:
        return BillingSettingsResponse(
            legal_name=customer.legal_name,
            email=customer.email,
            cpf_cnpj=customer.cpf_cnpj,
            postal_code=customer.postal_code,
            address=customer.address,
            address_number=customer.address_number,
            complement=customer.complement,
            province=customer.province,
            city=customer.city,
            state=customer.state,
            country=customer.country,
            cycle_close_day=customer.cycle_close_day,
            alert_enabled=customer.alert_enabled,
            promo_code=customer.promo_code,
            asaas_linked=bool(customer.asaas_customer_id),
            contracted_services=services,
        )

    def _method_response(self, row: BillingPaymentMethodModel) -> PaymentMethodResponse:
        return PaymentMethodResponse(
            id=row.id,
            billing_type=row.billing_type,
            brand=row.brand,
            last4=row.last4,
            holder_name=row.holder_name,
            is_primary=row.is_primary,
            credit_card_token=row.asaas_token,
        )
