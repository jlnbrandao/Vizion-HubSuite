"""Role Aggregate Root — owns Role ⇄ Permission association via permission IDs.

Does NOT import Permission entities. Cross-module validation happens in the
application layer via QueryBus (CheckPermissionsExistQuery).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from src.modules.roles.events.role_events import (
    PermissionsAssignedToRoleEvent,
    PermissionsRevokedFromRoleEvent,
    RoleCreatedEvent,
    RoleDeletedEvent,
    RoleUpdatedEvent,
)
from src.modules.roles.value_objects.role_description import RoleDescription
from src.modules.roles.value_objects.role_name import RoleName
from src.shared.domain.aggregate_root import AggregateRoot


@dataclass(eq=False, kw_only=True)
class Role(AggregateRoot):
    name: RoleName
    description: RoleDescription = field(default_factory=lambda: RoleDescription(value=""))
    permission_ids: set[UUID] = field(default_factory=set)
    is_active: bool = True

    @classmethod
    def create(
        cls,
        *,
        name: RoleName,
        description: RoleDescription | None = None,
    ) -> Role:
        role = cls(
            name=name,
            description=description or RoleDescription(value=""),
        )
        role.raise_event(RoleCreatedEvent(aggregate_id=role.id, name=name.value))
        return role

    def rename(self, name: RoleName) -> None:
        if self.name == name:
            return
        self.name = name
        self.touch()
        self.raise_event(RoleUpdatedEvent(aggregate_id=self.id, name=name.value))

    def change_description(self, description: RoleDescription) -> None:
        if self.description == description:
            return
        self.description = description
        self.touch()
        self.raise_event(RoleUpdatedEvent(aggregate_id=self.id, name=self.name.value))

    def assign_permissions(self, permission_ids: set[UUID]) -> None:
        """Add permissions. Idempotent for already-assigned IDs."""
        new_ids = permission_ids - self.permission_ids
        if not new_ids:
            return
        self.permission_ids |= new_ids
        self.touch()
        self.raise_event(
            PermissionsAssignedToRoleEvent(
                aggregate_id=self.id,
                role_name=self.name.value,
                permission_ids=tuple(sorted(new_ids, key=str)),
            )
        )

    def revoke_permissions(self, permission_ids: set[UUID]) -> None:
        removed = permission_ids & self.permission_ids
        if not removed:
            return
        self.permission_ids -= removed
        self.touch()
        self.raise_event(
            PermissionsRevokedFromRoleEvent(
                aggregate_id=self.id,
                role_name=self.name.value,
                permission_ids=tuple(sorted(removed, key=str)),
            )
        )

    def replace_permissions(self, permission_ids: set[UUID]) -> None:
        """Full sync of permission set (assign missing, revoke extras)."""
        to_add = permission_ids - self.permission_ids
        to_remove = self.permission_ids - permission_ids
        if to_add:
            self.assign_permissions(to_add)
        if to_remove:
            self.revoke_permissions(to_remove)

    def activate(self) -> None:
        if self.is_active:
            return
        self.is_active = True
        self.touch()
        self.raise_event(RoleUpdatedEvent(aggregate_id=self.id, name=self.name.value))

    def deactivate(self) -> None:
        if not self.is_active:
            return
        self.is_active = False
        self.touch()
        self.raise_event(RoleUpdatedEvent(aggregate_id=self.id, name=self.name.value))

    def mark_deleted(self) -> None:
        self.raise_event(RoleDeletedEvent(aggregate_id=self.id, name=self.name.value))

    def has_permission(self, permission_id: UUID) -> bool:
        return permission_id in self.permission_ids
