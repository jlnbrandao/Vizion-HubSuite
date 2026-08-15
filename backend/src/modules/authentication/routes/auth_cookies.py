"""httpOnly refresh-token cookie helpers for auth routes.

Over HTTPS the cookie uses the `__Host-` prefix, which browsers only accept when
it is Secure, has no Domain attribute and Path=/ — that makes it impossible for a
sibling subdomain to overwrite it. Plain HTTP (development) falls back to the
legacy name, since `__Host-` cookies would be rejected outright.
"""

from __future__ import annotations

from fastapi import Request, Response

from src.config.settings import Settings

LEGACY_REFRESH_COOKIE_NAME = "vizion_refresh_token"
LEGACY_REFRESH_COOKIE_PATH = "/api/v1/auth"
HOST_REFRESH_COOKIE_NAME = "__Host-vizion_refresh_token"
HOST_REFRESH_COOKIE_PATH = "/"

#: Readable (not httpOnly) flag so the SPA only calls /auth/refresh when a
#: session cookie actually exists — otherwise the login page would 401 on every load.
SESSION_HINT_COOKIE_NAME = "vizion_has_session"
SESSION_HINT_COOKIE_PATH = "/"

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
    response.set_cookie(
        key=SESSION_HINT_COOKIE_NAME,
        value="1",
        httponly=False,
        secure=settings.refresh_cookie_secure,
        samesite="lax",
        path=SESSION_HINT_COOKIE_PATH,
        max_age=settings.jwt_refresh_token_expire_days * 86_400,
    )


def clear_refresh_cookie(response: Response, settings: Settings) -> None:
    # Never emit a `__Host-` Set-Cookie over HTTP: browsers reject the prefix
    # unless the connection is HTTPS and the cookie is Secure + Path=/ + no Domain.
    cookies: list[tuple[str, str, bool]] = [
        (LEGACY_REFRESH_COOKIE_NAME, LEGACY_REFRESH_COOKIE_PATH, True),
        (SESSION_HINT_COOKIE_NAME, SESSION_HINT_COOKIE_PATH, False),
    ]
    if settings.refresh_cookie_secure:
        cookies.insert(
            0, (HOST_REFRESH_COOKIE_NAME, HOST_REFRESH_COOKIE_PATH, True)
        )

    for name, path, httponly in cookies:
        response.delete_cookie(
            key=name,
            path=path,
            secure=settings.refresh_cookie_secure,
            httponly=httponly,
            samesite="lax",
        )
