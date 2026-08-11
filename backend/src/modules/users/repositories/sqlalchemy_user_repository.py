"""SQLAlchemy User repository — persistence only, no business rules."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.users.entities.user import User
from src.modules.users.repositories.user_model import UserModel, UserRoleModel
from src.modules.users.repositories.user_repository import UserRepository
from src.modules.users.value_objects.email import Email
from src.modules.users.value_objects.full_name import FullName
from src.modules.users.value_objects.hashed_password import HashedPassword
from src.modules.users.value_objects.username import Username
from src.shared.infrastructure.session_context import get_current_session


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
        model = await self._session().get(UserModel, entity_id)
        if model is None:
            return None
        role_ids = await _load_role_ids(self._session(), entity_id)
        return _to_entity(model, role_ids)

    async def get_by_email(self, email: Email) -> User | None:
        stmt = select(UserModel).where(UserModel.email == email.value)
        result = await self._session().execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        role_ids = await _load_role_ids(self._session(), model.id)
        return _to_entity(model, role_ids)

    async def get_by_username(self, username: Username) -> User | None:
        stmt = select(UserModel).where(UserModel.username == username.value)
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
        model = await session.get(UserModel, entity.id)
        if model is None:
            raise ValueError(f"UserModel not found: {entity.id}")
        model.email = entity.email.value
        model.username = entity.username.value
        model.full_name = entity.full_name.value
        model.hashed_password = entity.hashed_password.value
        model.is_active = entity.is_active
        model.updated_at = entity.updated_at
        await self._sync_roles(entity)

    async def delete(self, entity: User) -> None:
        session = self._session()
        await session.execute(delete(UserRoleModel).where(UserRoleModel.user_id == entity.id))
        model = await session.get(UserModel, entity.id)
        if model is not None:
            await session.delete(model)

    async def exists(self, entity_id: UUID) -> bool:
        model = await self._session().get(UserModel, entity_id)
        return model is not None

    async def exists_by_email(self, email: Email) -> bool:
        stmt = select(UserModel.id).where(UserModel.email == email.value)
        result = await self._session().execute(stmt)
        return result.scalar_one_or_none() is not None

    async def exists_by_username(self, username: Username) -> bool:
        stmt = select(UserModel.id).where(UserModel.username == username.value)
        result = await self._session().execute(stmt)
        return result.scalar_one_or_none() is not None

    async def list_all(self, *, only_active: bool = False) -> list[User]:
        stmt = select(UserModel).order_by(UserModel.username)
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

        stmt = select(func.count()).select_from(UserModel)
        if only_active:
            stmt = stmt.where(UserModel.is_active.is_(True))
        result = await self._session().execute(stmt)
        return int(result.scalar_one())

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
