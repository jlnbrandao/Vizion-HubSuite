"""ABAC policy enforcer and CRUD."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select

from src.modules.iam.models import AccessPolicyModel
from src.shared.infrastructure.exceptions import ForbiddenError, NotFoundError
from src.shared.infrastructure.session_context import get_current_session
from src.shared.infrastructure.tenant_context import require_current_tenant_id

ROLE_RANKS: dict[str, int] = {
    "PLATFORM": 100,
    "ADMIN": 80,
    "MANAGER": 60,
    "OPERATOR": 40,
    "CLIENT": 20,
    "VIEWER": 10,
}


class PolicyEnforcer:
    def max_rank(self, role_names: list[str] | tuple[str, ...]) -> int:
        return max((ROLE_RANKS.get(name.upper(), 0) for name in role_names), default=0)

    def enforce(
        self,
        *,
        policies: list[AccessPolicyModel],
        subject_attrs: dict[str, Any],
        action: str,
        resource_attrs: dict[str, Any],
        env: dict[str, Any],
    ) -> bool:
        applicable = [
            p
            for p in policies
            if p.is_active
            and (not p.actions or action in p.actions or "*" in p.actions)
            and (
                not p.resource_types
                or resource_attrs.get("type") in p.resource_types
                or "*" in p.resource_types
            )
        ]
        applicable.sort(key=lambda p: p.priority)
        if not applicable:
            return True
        for policy in applicable:
            if self._match(policy.conditions, subject_attrs, resource_attrs, env):
                return policy.effect.lower() == "allow"
            # Allow-gates with unmet subject_outranks_target deny the action.
            if (
                policy.effect.lower() == "allow"
                and (policy.conditions or {}).get("subject_outranks_target")
            ):
                return False
        return True

    def _match(
        self,
        conditions: dict[str, Any],
        subject: dict[str, Any],
        resource: dict[str, Any],
        env: dict[str, Any],
    ) -> bool:
        if not conditions:
            return True
        if "min_role_rank" in conditions:
            if self.max_rank(subject.get("role_names") or []) < int(conditions["min_role_rank"]):
                return False
        if "subject_outranks_target" in conditions and conditions["subject_outranks_target"]:
            if self.max_rank(subject.get("role_names") or []) <= self.max_rank(
                resource.get("target_role_names") or []
            ):
                return False
        if "ip_in_allowlist" in conditions:
            allow = conditions["ip_in_allowlist"] or []
            if allow and env.get("ip") not in allow:
                return False
        if conditions.get("resource_owner_is_subject"):
            if resource.get("owner_id") != subject.get("user_id"):
                return False
        return True


class AbacService:
    def __init__(self) -> None:
        self.enforcer = PolicyEnforcer()

    async def create_policy(
        self,
        *,
        name: str,
        description: str = "",
        effect: str = "allow",
        actions: list[str] | None = None,
        resource_types: list[str] | None = None,
        conditions: dict[str, Any] | None = None,
        priority: int = 100,
    ) -> AccessPolicyModel:
        model = AccessPolicyModel(
            id=uuid4(),
            tenant_id=require_current_tenant_id(),
            name=name,
            description=description,
            effect=effect,
            actions=actions or [],
            resource_types=resource_types or [],
            conditions=conditions or {},
            priority=priority,
        )
        db = get_current_session()
        db.add(model)
        await db.flush()
        return model

    async def list_policies(self) -> list[AccessPolicyModel]:
        db = get_current_session()
        result = await db.execute(
            select(AccessPolicyModel)
            .where(AccessPolicyModel.tenant_id == require_current_tenant_id())
            .order_by(AccessPolicyModel.priority.asc())
        )
        return list(result.scalars().all())

    async def get_policy(self, policy_id: UUID) -> AccessPolicyModel:
        db = get_current_session()
        model = await db.get(AccessPolicyModel, policy_id)
        if model is None or model.tenant_id != require_current_tenant_id():
            raise NotFoundError("Policy not found")
        return model

    async def update_policy(self, policy_id: UUID, **fields: Any) -> AccessPolicyModel:
        model = await self.get_policy(policy_id)
        for key, value in fields.items():
            if value is not None and hasattr(model, key):
                setattr(model, key, value)
        await get_current_session().flush()
        return model

    async def delete_policy(self, policy_id: UUID) -> None:
        model = await self.get_policy(policy_id)
        await get_current_session().delete(model)

    async def enforce_or_raise(
        self,
        *,
        subject_attrs: dict[str, Any],
        action: str,
        resource_attrs: dict[str, Any],
        env: dict[str, Any],
    ) -> None:
        policies = await self.list_policies()
        if not self.enforcer.enforce(
            policies=policies,
            subject_attrs=subject_attrs,
            action=action,
            resource_attrs=resource_attrs,
            env=env,
        ):
            raise ForbiddenError("ABAC policy denied")
