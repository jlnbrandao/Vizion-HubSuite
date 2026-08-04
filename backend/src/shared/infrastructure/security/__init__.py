"""Shared security exports.

Note: FastAPI dependencies live in `dependencies` and are imported directly
to avoid circular imports with the DI container.
"""

from src.shared.infrastructure.security.current_user import CurrentUser
from src.shared.infrastructure.security.permission_codes import PermissionCode

__all__ = [
    "CurrentUser",
    "PermissionCode",
]
