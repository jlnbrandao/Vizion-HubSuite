"""SQLAlchemy User repository — persistence only, no business rules."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.roles.repositories.role_model import RoleModel
from src.modules.users.entities.user import User
from src.modules.users.repositories.user_model import UserModel, UserRoleModel
from src.modules.users.repositories.user_repository import UserRepository
from src.modules.users.value_objects.email import Email
from src.modules.users.value_objects.full_name import FullName
from src.modules.users.value_objects.hashed_password import HashedPassword
from src.modules.users.value_objects.username import Username
from src.shared.infrastructure.session_context import get_current_session
from src.shared.infrastructure.tenant_scope import apply_tenant_scope


async def _load_role_ids(session: AsyncSession, user_id: UUID) -> set[UUID]:
    stmt = select(UserRoleModel.role_id).where(UserRoleModel.user_id == user_id)
    result = await session.execute(stmt)
    return set(result.scalars().all())


def _to_entity(model: UserModel, role_ids: set[UUID]) -> User:
    return User(
        id=model.id,
        created_at=model.created_at,
        updated_at=model.updated_at,
        tenant_id=model.tenant_id,
        email=Email(value=model.email),
        username=Username(value=model.username),
        full_name=FullName(value=model.full_name),
        hashed_password=HashedPassword(value=model.hashed_password),
        role_ids=role_ids,
        is_active=model.is_active,
    )


class SqlAlchemyUserRepository(UserRepository):
    def _session(self) -> AsyncSession:
        return get_current_session()

    async def get_by_id(self, entity_id: UUID) -> User | None:
        stmt = apply_tenant_scope(
            select(UserModel).where(UserModel.id == entity_id),
            UserModel.tenant_id,
        )
        result = await self._session().execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        role_ids = await _load_role_ids(self._session(), entity_id)
        return _to_entity(model, role_ids)

    async def get_by_email(self, email: Email) -> User | None:
        stmt = apply_tenant_scope(
            select(UserModel).where(UserModel.email == email.value),
            UserModel.tenant_id,
        )
        result = await self._session().execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        role_ids = await _load_role_ids(self._session(), model.id)
        return _to_entity(model, role_ids)

    async def get_by_username(self, username: Username) -> User | None:
        stmt = apply_tenant_scope(
            select(UserModel).where(UserModel.username == username.value),
            UserModel.tenant_id,
        )
        result = await self._session().execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        role_ids = await _load_role_ids(self._session(), model.id)
        return _to_entity(model, role_ids)

    async def add(self, entity: User) -> None:
        session = self._session()
        model = UserModel(
            id=entity.id,
            tenant_id=entity.tenant_id,
            email=entity.email.value,
            username=entity.username.value,
            full_name=entity.full_name.value,
            hashed_password=entity.hashed_password.value,
            is_active=entity.is_active,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
        session.add(model)
        await self._sync_roles(entity)

    async def update(self, entity: User) -> None:
        session = self._session()
        stmt = apply_tenant_scope(
            select(UserModel).where(UserModel.id == entity.id),
            UserModel.tenant_id,
        )
        result = await session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            raise ValueError(f"UserModel not found: {entity.id}")
        row.email = entity.email.value
        row.username = entity.username.value
        row.full_name = entity.full_name.value
        row.hashed_password = entity.hashed_password.value
        row.is_active = entity.is_active
        row.updated_at = entity.updated_at
        await self._sync_roles(entity)

    async def delete(self, entity: User) -> None:
        session = self._session()
        await session.execute(delete(UserRoleModel).where(UserRoleModel.user_id == entity.id))
        stmt = apply_tenant_scope(
            select(UserModel).where(UserModel.id == entity.id),
            UserModel.tenant_id,
        )
        result = await session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is not None:
            await session.delete(model)

    async def exists(self, entity_id: UUID) -> bool:
        return await self.get_by_id(entity_id) is not None

    async def exists_by_email(self, email: Email) -> bool:
        stmt = apply_tenant_scope(
            select(UserModel.id).where(UserModel.email == email.value),
            UserModel.tenant_id,
        )
        result = await self._session().execute(stmt)
        return result.scalar_one_or_none() is not None

    async def exists_by_username(self, username: Username) -> bool:
        stmt = apply_tenant_scope(
            select(UserModel.id).where(UserModel.username == username.value),
            UserModel.tenant_id,
        )
        result = await self._session().execute(stmt)
        return result.scalar_one_or_none() is not None

    async def list_all(self, *, only_active: bool = False) -> list[User]:
        stmt = apply_tenant_scope(
            select(UserModel).order_by(UserModel.username),
            UserModel.tenant_id,
        )
        if only_active:
            stmt = stmt.where(UserModel.is_active.is_(True))
        result = await self._session().execute(stmt)
        users: list[User] = []
        for model in result.scalars().all():
            role_ids = await _load_role_ids(self._session(), model.id)
            users.append(_to_entity(model, role_ids))
        return users

    async def count(self, *, only_active: bool = False) -> int:
        from sqlalchemy import func

        stmt = apply_tenant_scope(
            select(func.count()).select_from(UserModel),
            UserModel.tenant_id,
        )
        if only_active:
            stmt = stmt.where(UserModel.is_active.is_(True))
        result = await self._session().execute(stmt)
        return int(result.scalar_one())

    async def find_primary_by_role_name_for_tenants(
        self,
        *,
        tenant_ids: set[UUID],
        role_name: str,
        only_active: bool = True,
    ) -> dict[UUID, User]:
        if not tenant_ids:
            return {}

        stmt = (
            select(UserModel)
            .join(UserRoleModel, UserRoleModel.user_id == UserModel.id)
            .join(RoleModel, RoleModel.id == UserRoleModel.role_id)
            .where(
                UserModel.tenant_id.in_(tenant_ids),
                RoleModel.tenant_id == UserModel.tenant_id,
                RoleModel.name == role_name,
            )
            .order_by(UserModel.tenant_id, UserModel.created_at.asc())
            .distinct(UserModel.tenant_id)
        )
        stmt = apply_tenant_scope(stmt, UserModel.tenant_id)
        if only_active:
            stmt = stmt.where(UserModel.is_active.is_(True))

        result = await self._session().execute(stmt)
        users: dict[UUID, User] = {}
        for model in result.scalars().all():
            role_ids = await _load_role_ids(self._session(), model.id)
            users[model.tenant_id] = _to_entity(model, role_ids)
        return users

    async def _sync_roles(self, entity: User) -> None:
        session = self._session()
        await session.execute(delete(UserRoleModel).where(UserRoleModel.user_id == entity.id))
        for role_id in entity.role_ids:
            session.add(
                UserRoleModel(
                    user_id=entity.id,
                    role_id=role_id,
                    tenant_id=entity.tenant_id,
                )
            )
