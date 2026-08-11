"""User input validators."""

from __future__ import annotations

from src.modules.users.value_objects.email import Email
from src.modules.users.value_objects.full_name import FullName
from src.modules.users.value_objects.plain_password import PlainPassword
from src.modules.users.value_objects.username import Username


def validate_email(raw: str) -> Email:
    return Email.from_primitive(raw)


def validate_username(raw: str) -> Username:
    return Username.from_primitive(raw)


def validate_full_name(raw: str) -> FullName:
    return FullName.from_primitive(raw)


def validate_plain_password(raw: str) -> PlainPassword:
    return PlainPassword.from_primitive(raw)
