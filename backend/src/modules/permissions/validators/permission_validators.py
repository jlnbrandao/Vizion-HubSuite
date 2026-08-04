"""Permission input validators — thin wrappers around Value Objects for API/DTO edges."""

from __future__ import annotations

from src.modules.permissions.value_objects.permission_code import PermissionCode
from src.modules.permissions.value_objects.permission_name import PermissionName


def validate_permission_code(raw: str) -> PermissionCode:
    return PermissionCode.from_primitive(raw)


def validate_permission_name(raw: str) -> PermissionName:
    return PermissionName.from_primitive(raw)
