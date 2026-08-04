"""Auth input validators."""

from __future__ import annotations

from src.modules.authentication.value_objects.refresh_token import RefreshToken
from src.modules.users.value_objects.email import Email


def validate_login_email(raw: str) -> Email:
    return Email.from_primitive(raw)


def validate_refresh_token(raw: str) -> RefreshToken:
    return RefreshToken.from_primitive(raw)
