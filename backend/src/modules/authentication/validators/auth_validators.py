"""Auth input validators."""

from __future__ import annotations

from src.modules.authentication.value_objects.refresh_token import RefreshToken
from src.modules.users.value_objects.email import Email
from src.modules.users.value_objects.username import Username


def validate_login_identifier(raw: str) -> Email | Username:
    cleaned = raw.strip()
    if "@" in cleaned:
        return Email.from_primitive(cleaned)
    return Username.from_primitive(cleaned)


def validate_refresh_token(raw: str) -> RefreshToken:
    return RefreshToken.from_primitive(raw)
