"""Role input validators — thin wrappers around Value Objects."""

from __future__ import annotations

from src.modules.roles.value_objects.role_description import RoleDescription
from src.modules.roles.value_objects.role_name import RoleName


def validate_role_name(raw: str) -> RoleName:
    return RoleName.from_primitive(raw)


def validate_role_description(raw: str) -> RoleDescription:
    return RoleDescription.from_primitive(raw)
