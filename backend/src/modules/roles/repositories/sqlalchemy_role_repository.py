"""SQLAlchemy Role repository — persistence only, no business rules."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.roles.entities.role import Role
from src.modules.roles.repositories.role_model import RoleModel, RolePermissionModel
from src.modules.roles.repositories.role_repository import RoleRepository
from src.modules.roles.value_objects.role_description import RoleDescription
from src.modules.roles.value_objects.role_name import RoleName
from src.shared.infrastructure.session_context import get_current_session
from src.shared.infrastructure.tenant_scope import apply_tenant_scope


async def _load_permission_ids(session: AsyncSession, role_id: UUID) -> set[UUID]:
    stmt = select(RolePermissionModel.permission_id).where(
        RolePermissionModel.role_id == role_id
    )
    result = await session.execute(stmt)
    return set(result.scalars().all())


def _to_entity(model: RoleModel, permission_ids: set[UUID]) -> Role:
    return Role(
        id=model.id,
        created_at=model.created_at,
        updated_at=model.updated_at,
        tenant_id=model.tenant_id,
        name=RoleName(value=model.name),
        description=RoleDescription(value=model.description),
        permission_ids=permission_ids,
        is_active=model.is_active,
    )


class SqlAlchemyRoleRepository(RoleRepository):
    def _session(self) -> AsyncSession:
        return get_current_session()

    async def get_by_id(self, entity_id: UUID) -> Role | None:
        stmt = apply_tenant_scope(
            select(RoleModel).where(RoleModel.id == entity_id),
            RoleModel.tenant_id,
        )
        result = await self._session().execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        permission_ids = await _load_permission_ids(self._session(), entity_id)
        return _to_entity(model, permission_ids)

    async def get_by_name(self, name: RoleName) -> Role | None:
        stmt = apply_tenant_scope(
            select(RoleModel).where(RoleModel.name == name.value),
            RoleModel.tenant_id,
        )
        result = await self._session().execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        permission_ids = await _load_permission_ids(self._session(), model.id)
        return _to_entity(model, permission_ids)

    async def add(self, entity: Role) -> None:
        session = self._session()
        model = RoleModel(
            id=entity.id,
            tenant_id=entity.tenant_id,
            name=entity.name.value,
            description=entity.description.value,
            is_active=entity.is_active,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
        session.add(model)
        await self._sync_permissions(entity)

    async def update(self, entity: Role) -> None:
        session = self._session()
        stmt = apply_tenant_scope(
            select(RoleModel).where(RoleModel.id == entity.id),
            RoleModel.tenant_id,
        )
        result = await session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            raise ValueError(f"RoleModel not found: {entity.id}")
        model.name = entity.name.value
        model.description = entity.description.value
        model.is_active = entity.is_active
        model.updated_at = entity.updated_at
        await self._sync_permissions(entity)

    async def delete(self, entity: Role) -> None:
        session = self._session()
        await session.execute(
            delete(RolePermissionModel).where(RolePermissionModel.role_id == entity.id)
        )
        stmt = apply_tenant_scope(
            select(RoleModel).where(RoleModel.id == entity.id),
            RoleModel.tenant_id,
        )
        result = await session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is not None:
            await session.delete(model)

    async def exists(self, entity_id: UUID) -> bool:
        return await self.get_by_id(entity_id) is not None

    async def exists_by_name(self, name: RoleName) -> bool:
        stmt = apply_tenant_scope(
            select(RoleModel.id).where(RoleModel.name == name.value),
            RoleModel.tenant_id,
        )
        result = await self._session().execute(stmt)
        return result.scalar_one_or_none() is not None

    async def list_all(self, *, only_active: bool = False) -> list[Role]:
        stmt = apply_tenant_scope(
            select(RoleModel).order_by(RoleModel.name),
            RoleModel.tenant_id,
        )
        if only_active:
            stmt = stmt.where(RoleModel.is_active.is_(True))
        result = await self._session().execute(stmt)
        roles: list[Role] = []
        for model in result.scalars().all():
            permission_ids = await _load_permission_ids(self._session(), model.id)
            roles.append(_to_entity(model, permission_ids))
        return roles

    async def find_by_ids(self, ids: set[UUID]) -> list[Role]:
        if not ids:
            return []
        stmt = apply_tenant_scope(
            select(RoleModel).where(RoleModel.id.in_(ids)),
            RoleModel.tenant_id,
        )
        result = await self._session().execute(stmt)
        roles: list[Role] = []
        for model in result.scalars().all():
            permission_ids = await _load_permission_ids(self._session(), model.id)
            roles.append(_to_entity(model, permission_ids))
        return roles

    async def count(self, *, only_active: bool = False) -> int:
        from sqlalchemy import func

        stmt = apply_tenant_scope(
            select(func.count()).select_from(RoleModel),
            RoleModel.tenant_id,
        )
        if only_active:
            stmt = stmt.where(RoleModel.is_active.is_(True))
        result = await self._session().execute(stmt)
        return int(result.scalar_one())

    async def _sync_permissions(self, entity: Role) -> None:
        session = self._session()
        await session.execute(
            delete(RolePermissionModel).where(RolePermissionModel.role_id == entity.id)
        )
        for permission_id in entity.permission_ids:
            session.add(
                RolePermissionModel(
                    role_id=entity.id,
                    permission_id=permission_id,
                    tenant_id=entity.tenant_id,
                )
            )
