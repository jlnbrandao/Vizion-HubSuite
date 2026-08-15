"""Audit event persistence and listing."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select, text

from src.modules.iam.models import AuditEventModel
from src.shared.infrastructure.request_context import get_request_id
from src.shared.infrastructure.session_context import get_current_session
from src.shared.infrastructure.tenant_context import (
    get_current_tenant_id,
    require_current_tenant_id,
)


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
        request_id: str | None = None,
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
            request_id=request_id or get_request_id(),
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
        request_id: str | None = None,
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
        if request_id:
            stmt = stmt.where(AuditEventModel.request_id == request_id)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def prune(self, *, retention_days: int) -> int:
        """Delete events older than the retention window, across every tenant.

        Runs `prune_audit_events` (migration 0017) so the delete is a single
        server-side statement; callers must be allowed to bypass RLS.
        """
        if retention_days < 1:
            raise ValueError("retention_days must be >= 1")
        result = await get_current_session().execute(
            text("SELECT prune_audit_events(:days)"), {"days": retention_days}
        )
        return int(result.scalar_one() or 0)
