"""Domain tests for Role aggregate."""

from __future__ import annotations

from uuid import uuid4

import pytest

from src.modules.roles.entities.role import Role
from src.modules.roles.events.role_events import (
    PermissionsAssignedToRoleEvent,
    RoleCreatedEvent,
)
from src.modules.roles.value_objects.role_name import RoleName


def test_role_name_normalizes_and_validates() -> None:
    name = RoleName.from_primitive("admin")
    assert name.value == "ADMIN"

    with pytest.raises(ValueError):
        RoleName(value="bad name")


def test_role_create_and_assign_permissions() -> None:
    role = Role.create(name=RoleName(value="MANAGER"))
    events = role.pull_domain_events()
    assert isinstance(events[0], RoleCreatedEvent)

    p1, p2 = uuid4(), uuid4()
    role.assign_permissions({p1, p2})
    assigned = role.pull_domain_events()
    assert len(assigned) == 1
    assert isinstance(assigned[0], PermissionsAssignedToRoleEvent)
    assert role.has_permission(p1)

    role.assign_permissions({p1})  # idempotent
    assert role.domain_events == []


def test_role_replace_permissions() -> None:
    role = Role.create(name=RoleName(value="OPERATOR"))
    role.pull_domain_events()

    a, b, c = uuid4(), uuid4(), uuid4()
    role.assign_permissions({a, b})
    role.pull_domain_events()

    role.replace_permissions({b, c})
    assert role.permission_ids == {b, c}
    assert len(role.pull_domain_events()) == 2  # assign c + revoke a
