"""Authentication HTTP routes — Login / Logout / Refresh."""

from __future__ import annotations

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Request, Response, status

from src.config.settings import Settings, get_settings
from src.modules.authentication.commands.auth_commands import (
    LoginCommand,
    LogoutCommand,
    RefreshTokenCommand,
)
from src.modules.authentication.dtos.auth_dtos import TokenPairDto
from src.modules.authentication.routes.auth_cookies import (
    REFRESH_COOKIE_NAME,
    clear_refresh_cookie,
    set_refresh_cookie,
)
from src.modules.authentication.routes.schemas import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    TokenResponse,
)
from src.shared.application.command_bus import CommandBus
from src.shared.infrastructure.di.container import Container
from src.shared.infrastructure.exceptions import UnauthorizedError

router = APIRouter(prefix="/auth", tags=["authentication"])


def _to_response(dto: TokenPairDto) -> TokenResponse:
    assert dto.user_id is not None
    return TokenResponse(
        access_token=dto.access_token,
        token_type=dto.token_type,
        expires_in=dto.expires_in,
        user_id=dto.user_id,
        email=dto.email,
        full_name=dto.full_name,
    )


def _refresh_token_from_request(request: Request, body_token: str | None) -> str:
    token = (body_token or "").strip() or request.cookies.get(REFRESH_COOKIE_NAME)
    if not token:
        raise UnauthorizedError("Missing refresh token")
    return token


@router.post("/login", response_model=TokenResponse)
@inject
async def login(
    body: LoginRequest,
    response: Response,
    command_bus: CommandBus = Depends(Provide[Container.command_bus]),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    result: TokenPairDto = await command_bus.execute(
        LoginCommand(login=body.login, password=body.password)
    )
    set_refresh_cookie(response, result.refresh_token, settings)
    return _to_response(result)


@router.post("/refresh", response_model=TokenResponse)
@inject
async def refresh(
    request: Request,
    response: Response,
    body: RefreshRequest | None = None,
    command_bus: CommandBus = Depends(Provide[Container.command_bus]),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    token = _refresh_token_from_request(
        request, body.refresh_token if body is not None else None
    )
    result: TokenPairDto = await command_bus.execute(
        RefreshTokenCommand(refresh_token=token)
    )
    set_refresh_cookie(response, result.refresh_token, settings)
    return _to_response(result)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
@inject
async def logout(
    request: Request,
    response: Response,
    body: LogoutRequest | None = None,
    command_bus: CommandBus = Depends(Provide[Container.command_bus]),
    settings: Settings = Depends(get_settings),
) -> None:
    try:
        token = _refresh_token_from_request(
            request, body.refresh_token if body is not None else None
        )
        await command_bus.execute(LogoutCommand(refresh_token=token))
    except UnauthorizedError:
        pass
    finally:
        clear_refresh_cookie(response, settings)
