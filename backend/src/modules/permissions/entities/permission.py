"""Permission Aggregate Root."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.modules.permissions.events.permission_events import (
    PermissionCreatedEvent,
    PermissionDeletedEvent,
    PermissionUpdatedEvent,
)
from src.modules.permissions.value_objects.permission_code import PermissionCode
from src.modules.permissions.value_objects.permission_name import PermissionName
from src.shared.domain.aggregate_root import AggregateRoot


@dataclass(eq=False, kw_only=True)
class Permission(AggregateRoot):
    tenant_id: UUID
    code: PermissionCode
    name: PermissionName
    description: str = ""
    is_active: bool = True

    @classmethod
    def create(
        cls,
        *,
        tenant_id: UUID,
        code: PermissionCode,
        name: PermissionName,
        description: str = "",
    ) -> Permission:
        permission = cls(
            tenant_id=tenant_id,
            code=code,
            name=name,
            description=description.strip(),
        )
        permission.raise_event(
            PermissionCreatedEvent(
                aggregate_id=permission.id,
                code=code.value,
                name=name.value,
            )
        )
        return permission

    def rename(self, name: PermissionName) -> None:
        if self.name == name:
            return
        self.name = name
        self.touch()
        self.raise_event(
            PermissionUpdatedEvent(
                aggregate_id=self.id,
                code=self.code.value,
                name=name.value,
            )
        )

    def change_description(self, description: str) -> None:
        cleaned = description.strip()
        if self.description == cleaned:
            return
        self.description = cleaned
        self.touch()
        self.raise_event(
            PermissionUpdatedEvent(
                aggregate_id=self.id,
                code=self.code.value,
                name=self.name.value,
            )
        )

    def activate(self) -> None:
        if self.is_active:
            return
        self.is_active = True
        self.touch()
        self.raise_event(
            PermissionUpdatedEvent(
                aggregate_id=self.id,
                code=self.code.value,
                name=self.name.value,
            )
        )

    def deactivate(self) -> None:
        if not self.is_active:
            return
        self.is_active = False
        self.touch()
        self.raise_event(
            PermissionUpdatedEvent(
                aggregate_id=self.id,
                code=self.code.value,
                name=self.name.value,
            )
        )

    def mark_deleted(self) -> None:
        self.raise_event(
            PermissionDeletedEvent(aggregate_id=self.id, code=self.code.value)
        )
