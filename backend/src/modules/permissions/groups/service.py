"""Permission bundles: named, service-scoped sets of permissions.

Roles compose bundles instead of enumerating dozens of codes. `role_permissions`
stays in place for fine-grained exceptions, so the effective code set of a role is
`role_permissions ∪ bundles`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4

from sqlalchemy import delete, select

from src.modules.permissions.repositories.permission_model import (
    PermissionGroupItemModel,
    PermissionGroupModel,
    PermissionModel,
    RolePermissionGroupModel,
)
from src.shared.infrastructure.exceptions import NotFoundError, ValidationError
from src.shared.infrastructure.security.permission_codes import PermissionCode
from src.shared.infrastructure.session_context import get_current_session
from src.shared.infrastructure.tenant_context import require_current_tenant_id


@dataclass(frozen=True, slots=True)
class PermissionGroupView:
    id: UUID
    slug: str
    service: str
    name: str
    description: str
    is_active: bool
    permission_ids: tuple[UUID, ...] = field(default_factory=tuple)
    permission_codes: tuple[str, ...] = field(default_factory=tuple)


class PermissionGroupService:
    async def list_groups(self, *, service: str | None = None) -> list[PermissionGroupView]:
        db = get_current_session()
        tenant_id = require_current_tenant_id()
        stmt = (
            select(PermissionGroupModel)
            .where(PermissionGroupModel.tenant_id == tenant_id)
            .order_by(PermissionGroupModel.service, PermissionGroupModel.slug)
        )
        if service:
            stmt = stmt.where(PermissionGroupModel.service == service)
        groups = list((await db.execute(stmt)).scalars().all())
        if not groups:
            return []

        rows = (
            await db.execute(
                select(
                    PermissionGroupItemModel.group_id,
                    PermissionModel.id,
                    PermissionModel.code,
                )
                .join(PermissionModel, PermissionModel.id == PermissionGroupItemModel.permission_id)
                .where(
                    PermissionGroupItemModel.tenant_id == tenant_id,
                    PermissionGroupItemModel.group_id.in_([group.id for group in groups]),
                )
                .order_by(PermissionModel.code)
            )
        ).all()

        by_group: dict[UUID, list[tuple[UUID, str]]] = {}
        for group_id, permission_id, code in rows:
            by_group.setdefault(group_id, []).append((permission_id, code))

        return [
            PermissionGroupView(
                id=group.id,
                slug=group.slug,
                service=group.service,
                name=group.name,
                description=group.description,
                is_active=group.is_active,
                permission_ids=tuple(item[0] for item in by_group.get(group.id, ())),
                permission_codes=tuple(item[1] for item in by_group.get(group.id, ())),
            )
            for group in groups
        ]

    async def upsert_group(
        self,
        *,
        slug: str,
        service: str,
        name: str,
        description: str = "",
        permission_ids: frozenset[UUID] | set[UUID] | None = None,
    ) -> PermissionGroupModel:
        slug = slug.strip().lower()
        service = service.strip().lower()
        if not slug or not service or not name.strip():
            raise ValidationError("slug, service and name are required")
        if not slug.startswith(f"{service}."):
            raise ValidationError("Bundle slug must be prefixed with its service")

        db = get_current_session()
        tenant_id = require_current_tenant_id()
        model = (
            await db.execute(
                select(PermissionGroupModel).where(
                    PermissionGroupModel.tenant_id == tenant_id,
                    PermissionGroupModel.slug == slug,
                )
            )
        ).scalar_one_or_none()

        if model is None:
            model = PermissionGroupModel(
                id=uuid4(),
                tenant_id=tenant_id,
                slug=slug,
                service=service,
                name=name.strip(),
                description=description.strip(),
            )
            db.add(model)
        else:
            model.service = service
            model.name = name.strip()
            model.description = description.strip()
        await db.flush()

        if permission_ids is not None:
            await self.replace_items(group_id=model.id, permission_ids=frozenset(permission_ids))
        return model

    async def replace_items(self, *, group_id: UUID, permission_ids: frozenset[UUID]) -> None:
        db = get_current_session()
        tenant_id = require_current_tenant_id()
        await self._require_group(group_id)

        if permission_ids:
            known = set(
                (
                    await db.execute(
                        select(PermissionModel.id).where(
                            PermissionModel.tenant_id == tenant_id,
                            PermissionModel.id.in_(permission_ids),
                        )
                    )
                )
                .scalars()
                .all()
            )
            unknown = permission_ids - known
            if unknown:
                raise ValidationError("Bundle references permissions of another tenant")

        await db.execute(
            delete(PermissionGroupItemModel).where(
                PermissionGroupItemModel.group_id == group_id,
                PermissionGroupItemModel.tenant_id == tenant_id,
            )
        )
        for permission_id in permission_ids:
            db.add(
                PermissionGroupItemModel(
                    group_id=group_id,
                    permission_id=permission_id,
                    tenant_id=tenant_id,
                )
            )
        await db.flush()

    async def delete_group(self, group_id: UUID) -> None:
        db = get_current_session()
        result = await db.execute(
            delete(PermissionGroupModel).where(
                PermissionGroupModel.id == group_id,
                PermissionGroupModel.tenant_id == require_current_tenant_id(),
            )
        )
        if not result.rowcount:
            raise NotFoundError("Permission bundle not found")

    async def groups_for_role(self, role_id: UUID) -> tuple[UUID, ...]:
        rows = (
            await get_current_session().execute(
                select(RolePermissionGroupModel.group_id).where(
                    RolePermissionGroupModel.role_id == role_id,
                    RolePermissionGroupModel.tenant_id == require_current_tenant_id(),
                )
            )
        ).all()
        return tuple(row[0] for row in rows)

    async def replace_role_groups(self, *, role_id: UUID, group_ids: frozenset[UUID]) -> None:
        db = get_current_session()
        tenant_id = require_current_tenant_id()
        for group_id in group_ids:
            await self._require_group(group_id)

        await db.execute(
            delete(RolePermissionGroupModel).where(
                RolePermissionGroupModel.role_id == role_id,
                RolePermissionGroupModel.tenant_id == tenant_id,
            )
        )
        for group_id in group_ids:
            db.add(
                RolePermissionGroupModel(
                    role_id=role_id,
                    group_id=group_id,
                    tenant_id=tenant_id,
                )
            )
        await db.flush()

    async def codes_for_roles(self, role_ids: frozenset[UUID]) -> frozenset[str]:
        """Permission codes the given roles inherit from bundles (both code forms)."""
        if not role_ids:
            return frozenset()
        rows = (
            await get_current_session().execute(
                select(PermissionModel.code, PermissionModel.legacy_code)
                .join(
                    PermissionGroupItemModel,
                    PermissionGroupItemModel.permission_id == PermissionModel.id,
                )
                .join(
                    RolePermissionGroupModel,
                    RolePermissionGroupModel.group_id == PermissionGroupItemModel.group_id,
                )
                .join(
                    PermissionGroupModel,
                    PermissionGroupModel.id == PermissionGroupItemModel.group_id,
                )
                .where(
                    RolePermissionGroupModel.tenant_id == require_current_tenant_id(),
                    RolePermissionGroupModel.role_id.in_(role_ids),
                    PermissionModel.is_active.is_(True),
                    PermissionGroupModel.is_active.is_(True),
                )
            )
        ).all()

        codes: set[str] = set()
        for code, legacy_code in rows:
            codes.add(code)
            if legacy_code:
                codes.add(legacy_code)
        return PermissionCode.expand(frozenset(codes))

    async def _require_group(self, group_id: UUID) -> PermissionGroupModel:
        model = (
            await get_current_session().execute(
                select(PermissionGroupModel).where(
                    PermissionGroupModel.id == group_id,
                    PermissionGroupModel.tenant_id == require_current_tenant_id(),
                )
            )
        ).scalar_one_or_none()
        if model is None:
            raise NotFoundError("Permission bundle not found")
        return model
