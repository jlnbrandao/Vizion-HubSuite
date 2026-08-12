"""Auth session persistence and revocation."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select, update

from src.modules.iam.models import AuthSessionModel
from src.shared.infrastructure.session_context import get_current_session
from src.shared.infrastructure.tenant_context import require_current_tenant_id


class SessionService:
    async def create(
        self,
        *,
        user_id: UUID,
        amr: tuple[str, ...] = (),
        ip_address: str | None = None,
        user_agent: str | None = None,
        expires_at: datetime,
    ) -> UUID:
        session_id = uuid4()
        model = AuthSessionModel(
            id=session_id,
            tenant_id=require_current_tenant_id(),
            user_id=user_id,
            amr=list(amr),
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=expires_at,
        )
        db = get_current_session()
        db.add(model)
        await db.flush()
        return session_id

    async def list_for_user(self, user_id: UUID) -> list[AuthSessionModel]:
        db = get_current_session()
        result = await db.execute(
            select(AuthSessionModel)
            .where(
                AuthSessionModel.user_id == user_id,
                AuthSessionModel.tenant_id == require_current_tenant_id(),
            )
            .order_by(AuthSessionModel.created_at.desc())
        )
        return list(result.scalars().all())

    async def revoke(self, session_id: UUID, user_id: UUID | None = None) -> bool:
        db = get_current_session()
        stmt = (
            update(AuthSessionModel)
            .where(
                AuthSessionModel.id == session_id,
                AuthSessionModel.tenant_id == require_current_tenant_id(),
                AuthSessionModel.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(UTC))
        )
        if user_id is not None:
            stmt = stmt.where(AuthSessionModel.user_id == user_id)
        result = await db.execute(stmt)
        return bool(result.rowcount)

    async def revoke_all_for_user(self, user_id: UUID) -> int:
        db = get_current_session()
        result = await db.execute(
            update(AuthSessionModel)
            .where(
                AuthSessionModel.user_id == user_id,
                AuthSessionModel.tenant_id == require_current_tenant_id(),
                AuthSessionModel.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(UTC))
        )
        return int(result.rowcount or 0)
