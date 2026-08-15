"""Resource ACL persistence and lookup.

An ACL entry is an exception scoped to a single resource. The engine consults this
service between the entitlement check and RBAC; see `security/authorization.py`.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import delete, or_, select

from src.modules.iam.models import ResourceAclModel
from src.shared.infrastructure.exceptions import NotFoundError, ValidationError
from src.shared.infrastructure.session_context import get_current_session
from src.shared.infrastructure.tenant_context import require_current_tenant_id

SUBJECT_TYPES = frozenset({"user", "role"})
EFFECTS = frozenset({"allow", "deny"})


class AclService:
    async def grant(
        self,
        *,
        subject_type: str,
        subject_id: UUID,
        resource_type: str,
        resource_id: str,
        action: str,
        effect: str = "allow",
        granted_by: UUID | None = None,
        expires_at: datetime | None = None,
    ) -> ResourceAclModel:
        subject_type = subject_type.strip().lower()
        effect = effect.strip().lower()
        if subject_type not in SUBJECT_TYPES:
            raise ValidationError("subject_type must be 'user' or 'role'")
        if effect not in EFFECTS:
            raise ValidationError("effect must be 'allow' or 'deny'")
        if not resource_type.strip() or not resource_id.strip() or not action.strip():
            raise ValidationError("resource_type, resource_id and action are required")

        db = get_current_session()
        tenant_id = require_current_tenant_id()
        existing = await db.execute(
            select(ResourceAclModel).where(
                ResourceAclModel.tenant_id == tenant_id,
                ResourceAclModel.subject_type == subject_type,
                ResourceAclModel.subject_id == subject_id,
                ResourceAclModel.resource_type == resource_type,
                ResourceAclModel.resource_id == resource_id,
                ResourceAclModel.action == action,
            )
        )
        model = existing.scalar_one_or_none()
        if model is not None:
            model.effect = effect
            model.granted_by = granted_by
            model.expires_at = expires_at
            await db.flush()
            return model

        model = ResourceAclModel(
            id=uuid4(),
            tenant_id=tenant_id,
            subject_type=subject_type,
            subject_id=subject_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            effect=effect,
            granted_by=granted_by,
            expires_at=expires_at,
        )
        db.add(model)
        await db.flush()
        return model

    async def list_entries(
        self,
        *,
        resource_type: str | None = None,
        resource_id: str | None = None,
        subject_id: UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ResourceAclModel]:
        stmt = (
            select(ResourceAclModel)
            .where(ResourceAclModel.tenant_id == require_current_tenant_id())
            .order_by(ResourceAclModel.created_at.desc())
            .limit(min(limit, 200))
            .offset(max(offset, 0))
        )
        if resource_type:
            stmt = stmt.where(ResourceAclModel.resource_type == resource_type)
        if resource_id:
            stmt = stmt.where(ResourceAclModel.resource_id == resource_id)
        if subject_id is not None:
            stmt = stmt.where(ResourceAclModel.subject_id == subject_id)
        result = await get_current_session().execute(stmt)
        return list(result.scalars().all())

    async def revoke(self, acl_id: UUID) -> None:
        db = get_current_session()
        result = await db.execute(
            delete(ResourceAclModel).where(
                ResourceAclModel.id == acl_id,
                ResourceAclModel.tenant_id == require_current_tenant_id(),
            )
        )
        if not result.rowcount:
            raise NotFoundError("ACL entry not found")

    async def effects_for(
        self,
        *,
        user_id: UUID,
        role_ids: tuple[UUID, ...],
        resource_type: str,
        resource_id: str,
        action: str,
    ) -> list[str]:
        """Live effects that apply to this subject/resource/action pair."""
        subjects = [
            (ResourceAclModel.subject_type == "user")
            & (ResourceAclModel.subject_id == user_id)
        ]
        if role_ids:
            subjects.append(
                (ResourceAclModel.subject_type == "role")
                & (ResourceAclModel.subject_id.in_(role_ids))
            )

        now = datetime.now(UTC)
        stmt = select(ResourceAclModel.effect).where(
            ResourceAclModel.tenant_id == require_current_tenant_id(),
            ResourceAclModel.resource_type == resource_type,
            ResourceAclModel.resource_id == resource_id,
            ResourceAclModel.action == action,
            or_(ResourceAclModel.expires_at.is_(None), ResourceAclModel.expires_at > now),
            or_(*subjects),
        )
        result = await get_current_session().execute(stmt)
        return [row[0] for row in result.all()]
