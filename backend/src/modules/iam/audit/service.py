"""Audit event persistence and listing."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select

from src.modules.iam.models import AuditEventModel
from src.shared.infrastructure.session_context import get_current_session
from src.shared.infrastructure.tenant_context import get_current_tenant_id, require_current_tenant_id


class AuditService:
    async def persist(
        self,
        *,
        action: str,
        actor_user_id: UUID | None = None,
        actor_type: str = "system",
        resource_type: str | None = None,
        resource_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        payload: dict[str, Any] | None = None,
        tenant_id: UUID | None = None,
    ) -> UUID:
        tid = tenant_id or get_current_tenant_id()
        if tid is None:
            raise RuntimeError("Cannot persist audit without tenant_id")
        event_id = uuid4()
        model = AuditEventModel(
            id=event_id,
            tenant_id=tid,
            actor_user_id=actor_user_id,
            actor_type=actor_type,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            payload=payload or {},
        )
        db = get_current_session()
        db.add(model)
        await db.flush()
        return event_id

    async def list_events(
        self,
        *,
        action: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AuditEventModel]:
        db = get_current_session()
        stmt = (
            select(AuditEventModel)
            .where(AuditEventModel.tenant_id == require_current_tenant_id())
            .order_by(AuditEventModel.created_at.desc())
            .limit(min(limit, 200))
            .offset(max(offset, 0))
        )
        if action:
            stmt = stmt.where(AuditEventModel.action == action)
        result = await db.execute(stmt)
        return list(result.scalars().all())
