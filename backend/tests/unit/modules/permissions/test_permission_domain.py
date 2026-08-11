"""Domain tests for Permission aggregate and value objects."""

from __future__ import annotations

from uuid import uuid4

import pytest

from src.modules.permissions.entities.permission import Permission
from src.modules.permissions.events.permission_events import (
    PermissionCreatedEvent,
    PermissionUpdatedEvent,
)
from src.modules.permissions.value_objects.permission_code import PermissionCode
from src.modules.permissions.value_objects.permission_name import PermissionName
from tests.unit.conftest import UNIVERSE_TENANT_ID


def test_permission_code_validates_format() -> None:
    code = PermissionCode.from_primitive("Users.Create")
    assert code.value == "users.create"
    assert code.resource == "users"
    assert code.action == "create"

    with pytest.raises(ValueError):
        PermissionCode(value="Invalid")


def test_permission_catalog_covers_all_codes() -> None:
    from src.shared.infrastructure.security.permission_codes import (
        PermissionAction,
        PermissionCode as CatalogCode,
    )

    assert set(CatalogCode.all_codes()) == {item.code for item in CatalogCode.catalog()}
    assert PermissionAction.CREATE in PermissionAction.all()
    assert CatalogCode.definition_for(CatalogCode.USERS_CREATE) is not None
    assert CatalogCode.definition_for(CatalogCode.USERS_CREATE).name == "Create users"


def test_permission_create_raises_event() -> None:
    permission = Permission.create(
        tenant_id=UNIVERSE_TENANT_ID,
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
        tenant_id=UNIVERSE_TENANT_ID,
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
