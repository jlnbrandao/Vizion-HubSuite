"""SQLAlchemy Permission repository — persistence only, no business rules."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from src.modules.permissions.entities.permission import Permission
from src.modules.permissions.repositories.permission_model import PermissionModel
from src.modules.permissions.repositories.permission_repository import PermissionRepository
from src.modules.permissions.value_objects.permission_code import PermissionCode
from src.modules.permissions.value_objects.permission_name import PermissionName
from src.shared.infrastructure.security.permission_codes import (
    PermissionCode as PermissionCatalog,
)
from src.shared.infrastructure.session_context import get_current_session
from src.shared.infrastructure.tenant_scope import apply_tenant_scope


def _code_matches(code: PermissionCode) -> ColumnElement[bool]:
    """Match a permission by its canonical code or its legacy alias."""
    wanted = {code.value, PermissionCatalog.canonical(code.value)}
    legacy = PermissionCatalog.legacy(code.value)
    if legacy:
        wanted.add(legacy)
    return or_(
        PermissionModel.code.in_(wanted),
        PermissionModel.legacy_code.in_(wanted),
    )


def _to_entity(model: PermissionModel) -> Permission:
    return Permission(
        id=model.id,
        created_at=model.created_at,
        updated_at=model.updated_at,
        tenant_id=model.tenant_id,
        code=PermissionCode(value=model.code),
        name=PermissionName(value=model.name),
        description=model.description,
        is_active=model.is_active,
    )


def _apply_entity(model: PermissionModel, entity: Permission) -> None:
    model.code = entity.code.value
    model.legacy_code = PermissionCatalog.legacy(entity.code.value)
    model.service = entity.code.service or PermissionCatalog.service_of(entity.code.value)
    model.resource = entity.code.resource
    model.action = entity.code.action
    model.name = entity.name.value
    model.description = entity.description
    model.is_active = entity.is_active
    model.updated_at = entity.updated_at


class SqlAlchemyPermissionRepository(PermissionRepository):
    def _session(self) -> AsyncSession:
        return get_current_session()

    async def get_by_id(self, entity_id: UUID) -> Permission | None:
        stmt = apply_tenant_scope(
            select(PermissionModel).where(PermissionModel.id == entity_id),
            PermissionModel.tenant_id,
        )
        result = await self._session().execute(stmt)
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def get_by_code(self, code: PermissionCode) -> Permission | None:
        stmt = apply_tenant_scope(
            select(PermissionModel).where(_code_matches(code)),
            PermissionModel.tenant_id,
        )
        result = await self._session().execute(stmt)
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def add(self, entity: Permission) -> None:
        model = PermissionModel(
            id=entity.id,
            tenant_id=entity.tenant_id,
            code=entity.code.value,
            legacy_code=PermissionCatalog.legacy(entity.code.value),
            service=entity.code.service or PermissionCatalog.service_of(entity.code.value),
            resource=entity.code.resource,
            action=entity.code.action,
            name=entity.name.value,
            description=entity.description,
            is_active=entity.is_active,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
        self._session().add(model)

    async def update(self, entity: Permission) -> None:
        stmt = apply_tenant_scope(
            select(PermissionModel).where(PermissionModel.id == entity.id),
            PermissionModel.tenant_id,
        )
        result = await self._session().execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            raise ValueError(f"PermissionModel not found: {entity.id}")
        _apply_entity(model, entity)

    async def delete(self, entity: Permission) -> None:
        stmt = apply_tenant_scope(
            select(PermissionModel).where(PermissionModel.id == entity.id),
            PermissionModel.tenant_id,
        )
        result = await self._session().execute(stmt)
        model = result.scalar_one_or_none()
        if model is not None:
            await self._session().delete(model)

    async def exists(self, entity_id: UUID) -> bool:
        return await self.get_by_id(entity_id) is not None

    async def exists_by_code(self, code: PermissionCode) -> bool:
        stmt = apply_tenant_scope(
            select(PermissionModel.id).where(_code_matches(code)),
            PermissionModel.tenant_id,
        )
        result = await self._session().execute(stmt)
        return result.scalar_one_or_none() is not None

    async def list_all(
        self,
        *,
        only_active: bool = False,
        resource: str | None = None,
        action: str | None = None,
    ) -> list[Permission]:
        stmt = apply_tenant_scope(
            select(PermissionModel).order_by(PermissionModel.code),
            PermissionModel.tenant_id,
        )
        if only_active:
            stmt = stmt.where(PermissionModel.is_active.is_(True))
        if resource:
            stmt = stmt.where(PermissionModel.resource == resource)
        if action:
            stmt = stmt.where(PermissionModel.action == action)
        result = await self._session().execute(stmt)
        return [_to_entity(m) for m in result.scalars().all()]

    async def find_by_ids(self, ids: set[UUID]) -> list[Permission]:
        if not ids:
            return []
        stmt = apply_tenant_scope(
            select(PermissionModel).where(PermissionModel.id.in_(ids)),
            PermissionModel.tenant_id,
        )
        result = await self._session().execute(stmt)
        return [_to_entity(m) for m in result.scalars().all()]

    async def count(self, *, only_active: bool = False) -> int:
        from sqlalchemy import func

        stmt = apply_tenant_scope(
            select(func.count()).select_from(PermissionModel),
            PermissionModel.tenant_id,
        )
        if only_active:
            stmt = stmt.where(PermissionModel.is_active.is_(True))
        result = await self._session().execute(stmt)
        return int(result.scalar_one())
