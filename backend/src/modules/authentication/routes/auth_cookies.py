"""httpOnly refresh-token cookie helpers for auth routes.

Over HTTPS the cookie uses the `__Host-` prefix, which browsers only accept when
it is Secure, has no Domain attribute and Path=/ — that makes it impossible for a
sibling subdomain to overwrite it. Plain HTTP (development) falls back to the
legacy name, since `__Host-` cookies would be rejected outright.
"""

from __future__ import annotations

from fastapi import Request, Response

from src.config.settings import Settings

LEGACY_REFRESH_COOKIE_NAME = "lanstar_refresh_token"
LEGACY_REFRESH_COOKIE_PATH = "/api/v1/auth"
HOST_REFRESH_COOKIE_NAME = "__Host-lanstar_refresh_token"
HOST_REFRESH_COOKIE_PATH = "/"

# Kept for callers that only need the development/legacy name.
REFRESH_COOKIE_NAME = LEGACY_REFRESH_COOKIE_NAME
REFRESH_COOKIE_PATH = LEGACY_REFRESH_COOKIE_PATH


def refresh_cookie_name(settings: Settings) -> str:
    if settings.refresh_cookie_secure:
        return HOST_REFRESH_COOKIE_NAME
    return LEGACY_REFRESH_COOKIE_NAME


def refresh_cookie_path(settings: Settings) -> str:
    if settings.refresh_cookie_secure:
        return HOST_REFRESH_COOKIE_PATH
    return LEGACY_REFRESH_COOKIE_PATH


def read_refresh_cookie(request: Request) -> str | None:
    """Accept either name so tokens issued before a TLS switch keep working."""
    return request.cookies.get(HOST_REFRESH_COOKIE_NAME) or request.cookies.get(
        LEGACY_REFRESH_COOKIE_NAME
    )


def set_refresh_cookie(response: Response, token: str, settings: Settings) -> None:
    response.set_cookie(
        key=refresh_cookie_name(settings),
        value=token,
        httponly=True,
        secure=settings.refresh_cookie_secure,
        samesite="lax",
        path=refresh_cookie_path(settings),
        max_age=settings.jwt_refresh_token_expire_days * 86_400,
    )


def clear_refresh_cookie(response: Response, settings: Settings) -> None:
    # Clear both variants: the active one and any cookie left from the other scheme.
    for name, path in (
        (HOST_REFRESH_COOKIE_NAME, HOST_REFRESH_COOKIE_PATH),
        (LEGACY_REFRESH_COOKIE_NAME, LEGACY_REFRESH_COOKIE_PATH),
    ):
        response.delete_cookie(
            key=name,
            path=path,
            secure=settings.refresh_cookie_secure,
            httponly=True,
            samesite="lax",
        )
