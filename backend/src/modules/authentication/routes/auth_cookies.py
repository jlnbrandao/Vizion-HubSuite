"""httpOnly refresh-token cookie helpers for auth routes."""

from __future__ import annotations

from fastapi import Response

from src.config.settings import Settings

REFRESH_COOKIE_NAME = "lanstar_refresh_token"
REFRESH_COOKIE_PATH = "/api/v1/auth"


def set_refresh_cookie(response: Response, token: str, settings: Settings) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=not settings.is_development,
        samesite="lax",
        path=REFRESH_COOKIE_PATH,
        max_age=settings.jwt_refresh_token_expire_days * 86_400,
    )


def clear_refresh_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path=REFRESH_COOKIE_PATH,
        secure=not settings.is_development,
        httponly=True,
        samesite="lax",
    )
