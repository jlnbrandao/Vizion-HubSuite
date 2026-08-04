"""Domain tests for Permission aggregate and value objects."""

from __future__ import annotations

import pytest

from src.modules.permissions.entities.permission import Permission
from src.modules.permissions.events.permission_events import (
    PermissionCreatedEvent,
    PermissionUpdatedEvent,
)
from src.modules.permissions.value_objects.permission_code import PermissionCode
from src.modules.permissions.value_objects.permission_name import PermissionName


def test_permission_code_validates_format() -> None:
    code = PermissionCode.from_primitive("Users.Create")
    assert code.value == "users.create"
    assert code.resource == "users"
    assert code.action == "create"

    with pytest.raises(ValueError):
        PermissionCode(value="Invalid")


def test_permission_create_raises_event() -> None:
    permission = Permission.create(
        code=PermissionCode(value="users.read"),
        name=PermissionName(value="Read Users"),
        description="List users",
    )
    events = permission.pull_domain_events()
    assert len(events) == 1
    assert isinstance(events[0], PermissionCreatedEvent)
    assert events[0].code == "users.read"


def test_permission_rename_is_idempotent() -> None:
    permission = Permission.create(
        code=PermissionCode(value="roles.read"),
        name=PermissionName(value="Read Roles"),
    )
    permission.pull_domain_events()

    permission.rename(PermissionName(value="Read Roles"))
    assert permission.domain_events == []

    permission.rename(PermissionName(value="View Roles"))
    events = permission.pull_domain_events()
    assert len(events) == 1
    assert isinstance(events[0], PermissionUpdatedEvent)
