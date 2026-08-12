"""Tenant auth policies, lockout, password history."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select, update

from src.modules.iam.models import PasswordHistoryModel, TenantAuthPolicyModel
from src.modules.users.repositories.user_model import UserModel
from src.modules.users.services.password_hasher import PasswordHasher
from src.modules.users.value_objects.hashed_password import HashedPassword
from src.modules.users.value_objects.plain_password import PlainPassword
from src.shared.infrastructure.exceptions import UnauthorizedError, ValidationError
from src.shared.infrastructure.session_context import get_current_session
from src.shared.infrastructure.tenant_context import require_current_tenant_id


class AuthPolicyService:
    async def get_or_create(self) -> TenantAuthPolicyModel:
        db = get_current_session()
        tenant_id = require_current_tenant_id()
        result = await db.execute(
            select(TenantAuthPolicyModel).where(TenantAuthPolicyModel.tenant_id == tenant_id)
        )
        policy = result.scalar_one_or_none()
        if policy is not None:
            return policy
        policy = TenantAuthPolicyModel(id=uuid4(), tenant_id=tenant_id)
        db.add(policy)
        await db.flush()
        return policy

    async def update(self, **fields: object) -> TenantAuthPolicyModel:
        policy = await self.get_or_create()
        for key, value in fields.items():
            if hasattr(policy, key) and value is not None:
                setattr(policy, key, value)
        policy.updated_at = datetime.now(UTC)
        await get_current_session().flush()
        return policy

    def assert_ip_allowed(self, policy: TenantAuthPolicyModel, ip: str | None) -> None:
        if not policy.ip_allowlist:
            return
        if not ip or ip not in policy.ip_allowlist:
            raise UnauthorizedError("Login not allowed from this network")

    async def assert_not_locked(self, user_id: UUID) -> None:
        db = get_current_session()
        result = await db.execute(select(UserModel).where(UserModel.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            return
        if user.locked_until and user.locked_until > datetime.now(UTC):
            raise UnauthorizedError("Account temporarily locked")

    async def record_failed_login(self, user_id: UUID, policy: TenantAuthPolicyModel) -> None:
        db = get_current_session()
        result = await db.execute(select(UserModel).where(UserModel.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            return
        user.failed_login_count = (user.failed_login_count or 0) + 1
        if user.failed_login_count >= policy.max_failed_attempts:
            user.locked_until = datetime.now(UTC) + timedelta(minutes=policy.lockout_minutes)
            user.failed_login_count = 0
        await db.flush()

    async def clear_failed_login(self, user_id: UUID) -> None:
        db = get_current_session()
        await db.execute(
            update(UserModel)
            .where(UserModel.id == user_id)
            .values(failed_login_count=0, locked_until=None)
        )

    async def assert_password_not_reused(
        self,
        *,
        user_id: UUID,
        plain: PlainPassword,
        hasher: PasswordHasher,
        history_count: int,
    ) -> None:
        if history_count <= 0:
            return
        db = get_current_session()
        result = await db.execute(
            select(PasswordHistoryModel)
            .where(
                PasswordHistoryModel.user_id == user_id,
                PasswordHistoryModel.tenant_id == require_current_tenant_id(),
            )
            .order_by(PasswordHistoryModel.created_at.desc())
            .limit(history_count)
        )
        for row in result.scalars().all():
            if hasher.verify(plain, HashedPassword.from_primitive(row.hashed_password)):
                raise ValidationError("Password was used recently")

    async def add_password_history(self, user_id: UUID, hashed: str) -> None:
        db = get_current_session()
        db.add(
            PasswordHistoryModel(
                id=uuid4(),
                tenant_id=require_current_tenant_id(),
                user_id=user_id,
                hashed_password=hashed,
            )
        )
        await db.flush()

    def password_expired(self, policy: TenantAuthPolicyModel, password_changed_at: datetime | None) -> bool:
        if policy.password_max_age_days <= 0:
            return False
        if password_changed_at is None:
            return True
        age = datetime.now(UTC) - password_changed_at
        return age > timedelta(days=policy.password_max_age_days)
