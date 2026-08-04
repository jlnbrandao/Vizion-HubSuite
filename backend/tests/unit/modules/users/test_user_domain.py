"""Domain tests for User aggregate and value objects."""

from __future__ import annotations

from uuid import uuid4

import pytest

from src.modules.users.entities.user import User
from src.modules.users.events.user_events import (
    RolesAssignedToUserEvent,
    UserCreatedEvent,
    UserPasswordChangedEvent,
)
from src.modules.users.value_objects.email import Email
from src.modules.users.value_objects.full_name import FullName
from src.modules.users.value_objects.hashed_password import HashedPassword


def test_email_normalizes_and_validates() -> None:
    email = Email.from_primitive("Admin@Example.COM")
    assert email.value == "admin@example.com"

    with pytest.raises(ValueError):
        Email(value="not-an-email")


def test_user_create_raises_event() -> None:
    user = User.create(
        email=Email(value="a@b.com"),
        full_name=FullName(value="Ada Lovelace"),
        hashed_password=HashedPassword(value="x" * 60),
    )
    events = user.pull_domain_events()
    assert isinstance(events[0], UserCreatedEvent)
    assert events[0].email == "a@b.com"


def test_user_assign_roles_and_change_password() -> None:
    user = User.create(
        email=Email(value="u@x.com"),
        full_name=FullName(value="User Name"),
        hashed_password=HashedPassword(value="old" + ("x" * 57)),
    )
    user.pull_domain_events()

    role_id = uuid4()
    user.assign_roles({role_id})
    events = user.pull_domain_events()
    assert isinstance(events[0], RolesAssignedToUserEvent)
    assert user.has_role(role_id)

    user.change_password(HashedPassword(value="new" + ("y" * 57)))
    pwd_events = user.pull_domain_events()
    assert isinstance(pwd_events[0], UserPasswordChangedEvent)
