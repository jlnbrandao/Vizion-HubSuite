"""SQLAlchemy Tenant repository — persistence only, no business rules."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.tenants.entities.tenant import Tenant
from src.modules.tenants.repositories.tenant_model import TenantModel
from src.modules.tenants.repositories.tenant_repository import TenantRepository
from src.modules.tenants.value_objects.tenant_slug import TenantSlug
from src.shared.infrastructure.session_context import get_current_session
from src.shared.infrastructure.tenant_context import get_rls_bypass


def _to_entity(model: TenantModel) -> Tenant:
    return Tenant(
        id=model.id,
        created_at=model.created_at,
        updated_at=model.updated_at,
        slug=TenantSlug(value=model.slug),
        name=model.name,
        is_active=model.is_active,
    )


def _apply_entity(model: TenantModel, entity: Tenant) -> None:
    model.slug = entity.slug.value
    model.name = entity.name
    model.is_active = entity.is_active
    model.updated_at = entity.updated_at


class SqlAlchemyTenantRepository(TenantRepository):
    def _session(self) -> AsyncSession:
        return get_current_session()

    async def get_by_id(self, entity_id: UUID) -> Tenant | None:
        model = await self._session().get(TenantModel, entity_id)
        return _to_entity(model) if model else None

    async def get_by_slug(self, slug: TenantSlug) -> Tenant | None:
        # Host resolution runs before tenant GUC is set — use SECURITY DEFINER helper.
        if not get_rls_bypass():
            result = await self._session().execute(
                text(
                    "SELECT id, slug, name, is_active, created_at, updated_at "
                    "FROM resolve_tenant_by_slug(:slug)"
                ),
                {"slug": slug.value},
            )
            row = result.mappings().first()
            if row is None:
                return None
            return Tenant(
                id=row["id"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                slug=TenantSlug(value=row["slug"]),
                name=row["name"],
                is_active=row["is_active"],
            )

        stmt = select(TenantModel).where(TenantModel.slug == slug.value)
        result = await self._session().execute(stmt)
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def list_all(self, *, only_active: bool = False) -> list[Tenant]:
        stmt = select(TenantModel).order_by(TenantModel.slug)
        if only_active:
            stmt = stmt.where(TenantModel.is_active.is_(True))
        result = await self._session().execute(stmt)
        return [_to_entity(model) for model in result.scalars().all()]

    async def add(self, entity: Tenant) -> None:
        model = TenantModel(
            id=entity.id,
            slug=entity.slug.value,
            name=entity.name,
            is_active=entity.is_active,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
        self._session().add(model)

    async def update(self, entity: Tenant) -> None:
        model = await self._session().get(TenantModel, entity.id)
        if model is None:
            raise ValueError(f"TenantModel not found: {entity.id}")
        _apply_entity(model, entity)

    async def delete(self, entity: Tenant) -> None:
        model = await self._session().get(TenantModel, entity.id)
        if model is not None:
            await self._session().delete(model)

    async def exists(self, entity_id: UUID) -> bool:
        model = await self._session().get(TenantModel, entity_id)
        return model is not None
