"""Service catalog and entitlement persistence.

The authorization engine asks this service one question — "is this tenant
entitled to this service?" — before RBAC runs. Platform administration uses the
same service to attach, suspend and quota services per tenant.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import or_, select

from src.modules.services.catalog import DEFAULT_SERVICE_SLUGS, PLATFORM_TENANT_SLUG
from src.modules.services.models import (
    ENTITLED_STATUSES,
    STATUS_ACTIVE,
    TENANT_SERVICE_STATUSES,
    ServiceModel,
    TenantServiceModel,
)
from src.shared.infrastructure.exceptions import NotFoundError, ValidationError
from src.shared.infrastructure.session_context import get_current_session
from src.shared.infrastructure.tenant_context import bind_rls_bypass, unbind_rls_bypass


@dataclass(frozen=True, slots=True)
class TenantServiceView:
    """A service as offered to one tenant, contract included when there is one."""

    service_id: UUID
    slug: str
    namespace: str
    name: str
    description: str
    version: str
    is_core: bool
    is_active: bool
    status: str | None
    plan: str | None
    quotas: dict[str, Any]
    expires_at: datetime | None

    @property
    def entitled(self) -> bool:
        return self.is_active and self.status in ENTITLED_STATUSES


class ServiceCatalogService:
    async def list_services(self, *, only_active: bool = False) -> list[ServiceModel]:
        stmt = select(ServiceModel).order_by(ServiceModel.slug)
        if only_active:
            stmt = stmt.where(ServiceModel.is_active.is_(True))
        result = await get_current_session().execute(stmt)
        return list(result.scalars().all())

    async def get_by_slug(self, slug: str) -> ServiceModel:
        result = await get_current_session().execute(
            select(ServiceModel).where(ServiceModel.slug == slug.strip().lower())
        )
        model = result.scalar_one_or_none()
        if model is None:
            raise NotFoundError(f"Unknown service: {slug}")
        return model

    async def entitled_namespaces(self, tenant_id: UUID) -> frozenset[str]:
        """Namespaces the tenant may use right now."""
        now = datetime.now(UTC)
        stmt = (
            select(ServiceModel.namespace, TenantServiceModel.expires_at)
            .join(TenantServiceModel, TenantServiceModel.service_id == ServiceModel.id)
            .where(
                TenantServiceModel.tenant_id == tenant_id,
                TenantServiceModel.status.in_(ENTITLED_STATUSES),
                ServiceModel.is_active.is_(True),
            )
        )
        result = await get_current_session().execute(stmt)
        # A NULL expires_at means the contract has no end date.
        return frozenset(
            namespace
            for namespace, expires_at in result.all()
            if expires_at is None or expires_at > now
        )

    async def list_for_tenant(self, tenant_id: UUID) -> list[TenantServiceView]:
        """Whole catalog plus this tenant's contract for each entry."""
        stmt = (
            select(ServiceModel, TenantServiceModel)
            .outerjoin(
                TenantServiceModel,
                (TenantServiceModel.service_id == ServiceModel.id)
                & (TenantServiceModel.tenant_id == tenant_id),
            )
            .order_by(ServiceModel.slug)
        )
        result = await get_current_session().execute(stmt)
        views: list[TenantServiceView] = []
        for service, contract in result.all():
            quotas = dict(service.default_quotas or {})
            if contract is not None:
                quotas.update(contract.quotas or {})
            views.append(
                TenantServiceView(
                    service_id=service.id,
                    slug=service.slug,
                    namespace=service.namespace,
                    name=service.name,
                    description=service.description,
                    version=service.version,
                    is_core=service.is_core,
                    is_active=service.is_active,
                    status=contract.status if contract else None,
                    plan=contract.plan if contract else None,
                    quotas=quotas,
                    expires_at=contract.expires_at if contract else None,
                )
            )
        return views

    async def set_status(
        self,
        *,
        tenant_id: UUID,
        service_slug: str,
        status: str,
        plan: str | None = None,
        quotas: dict[str, Any] | None = None,
        expires_at: datetime | None = None,
    ) -> TenantServiceModel:
        """Attach, re-plan or suspend one service for one tenant (idempotent)."""
        status = status.strip().lower()
        if status not in TENANT_SERVICE_STATUSES:
            raise ValidationError(
                f"status must be one of: {', '.join(sorted(TENANT_SERVICE_STATUSES))}"
            )

        service = await self.get_by_slug(service_slug)
        if service.is_core and status not in ENTITLED_STATUSES:
            raise ValidationError(
                f"'{service.slug}' is a core service and cannot be disabled"
            )
        if service.tenant_only:
            tenant_slug = await self._tenant_slug(tenant_id)
            if tenant_slug == PLATFORM_TENANT_SLUG:
                raise ValidationError(
                    f"'{service.slug}' is a tenant-only service and cannot be "
                    "entitled on the platform tenant"
                )
            if status not in ENTITLED_STATUSES:
                raise ValidationError(
                    f"'{service.slug}' is mandatory for product tenants and cannot be disabled"
                )

        db = get_current_session()
        result = await db.execute(
            select(TenantServiceModel).where(
                TenantServiceModel.tenant_id == tenant_id,
                TenantServiceModel.service_id == service.id,
            )
        )
        contract = result.scalar_one_or_none()
        now = datetime.now(UTC)

        if contract is None:
            contract = TenantServiceModel(
                id=uuid4(),
                tenant_id=tenant_id,
                service_id=service.id,
                plan=plan or "standard",
                status=status,
                quotas=quotas or {},
                activated_at=now if status in ENTITLED_STATUSES else None,
                expires_at=expires_at,
            )
            db.add(contract)
        else:
            if contract.status not in ENTITLED_STATUSES and status in ENTITLED_STATUSES:
                contract.activated_at = now
            contract.status = status
            if plan is not None:
                contract.plan = plan
            if quotas is not None:
                contract.quotas = quotas
            contract.expires_at = expires_at
        await db.flush()
        return contract

    async def quota(self, *, tenant_id: UUID, namespace: str, key: str) -> int | None:
        """Effective quota value, tenant override winning over the default."""
        stmt = (
            select(ServiceModel.default_quotas, TenantServiceModel.quotas)
            .join(TenantServiceModel, TenantServiceModel.service_id == ServiceModel.id)
            .where(
                TenantServiceModel.tenant_id == tenant_id,
                ServiceModel.namespace == namespace,
            )
        )
        result = await get_current_session().execute(stmt)
        row = result.first()
        if row is None:
            return None
        defaults, overrides = row
        merged = {**(defaults or {}), **(overrides or {})}
        value = merged.get(key)
        return int(value) if isinstance(value, int | float | str) and str(value).isdigit() else None

    async def ensure_default_services(self, tenant_id: UUID) -> None:
        """A brand-new tenant starts with the services that ship enabled.

        Core services are mandatory; the rest of this set is a product decision
        (see `DEFAULT_SERVICE_SLUGS`), and the platform may suspend those later.
        """
        result = await get_current_session().execute(
            select(ServiceModel).where(
                or_(
                    ServiceModel.is_core.is_(True),
                    ServiceModel.slug.in_(DEFAULT_SERVICE_SLUGS),
                )
            )
        )
        tenant_slug = await self._tenant_slug(tenant_id)
        for service in result.scalars().all():
            if service.tenant_only and tenant_slug == PLATFORM_TENANT_SLUG:
                continue
            await self.set_status(
                tenant_id=tenant_id, service_slug=service.slug, status=STATUS_ACTIVE
            )

    async def _tenant_slug(self, tenant_id: UUID) -> str | None:
        from src.modules.tenants.repositories.tenant_model import TenantModel

        result = await get_current_session().execute(
            select(TenantModel.slug).where(TenantModel.id == tenant_id)
        )
        return result.scalar_one_or_none()


class PlatformServiceCatalog:
    """Cross-tenant view of the catalog, used by PLATFORM administration.

    Reads bypass RLS on purpose: the platform operator manages contracts of every
    tenant. Endpoints are gated by `tenants.*` / `dashboard.platform` permissions.
    """

    def __init__(self, catalog: ServiceCatalogService) -> None:
        self._catalog = catalog

    async def list_for_tenant(self, tenant_id: UUID) -> list[TenantServiceView]:
        token = bind_rls_bypass(True)
        try:
            return await self._catalog.list_for_tenant(tenant_id)
        finally:
            unbind_rls_bypass(token)

    async def set_status(self, **kwargs: Any) -> TenantServiceModel:
        token = bind_rls_bypass(True)
        try:
            return await self._catalog.set_status(**kwargs)
        finally:
            unbind_rls_bypass(token)

    async def list_services(self) -> list[ServiceModel]:
        token = bind_rls_bypass(True)
        try:
            return await self._catalog.list_services()
        finally:
            unbind_rls_bypass(token)
