"""Authentication HTTP routes — Login / Logout / Refresh."""

from __future__ import annotations

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, status

from src.modules.authentication.commands.auth_commands import (
    LoginCommand,
    LogoutCommand,
    RefreshTokenCommand,
)
from src.modules.authentication.dtos.auth_dtos import TokenPairDto
from src.modules.authentication.routes.schemas import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    TokenResponse,
)
from src.shared.application.command_bus import CommandBus
from src.shared.infrastructure.di.container import Container

router = APIRouter(prefix="/auth", tags=["authentication"])


def _to_response(dto: TokenPairDto) -> TokenResponse:
    assert dto.user_id is not None
    return TokenResponse(
        access_token=dto.access_token,
        refresh_token=dto.refresh_token,
        token_type=dto.token_type,
        expires_in=dto.expires_in,
        user_id=dto.user_id,
        email=dto.email,
        full_name=dto.full_name,
    )


@router.post("/login", response_model=TokenResponse)
@inject
async def login(
    body: LoginRequest,
    command_bus: CommandBus = Depends(Provide[Container.command_bus]),
) -> TokenResponse:
    result: TokenPairDto = await command_bus.execute(
        LoginCommand(email=body.email, password=body.password)
    )
    return _to_response(result)


@router.post("/refresh", response_model=TokenResponse)
@inject
async def refresh(
    body: RefreshRequest,
    command_bus: CommandBus = Depends(Provide[Container.command_bus]),
) -> TokenResponse:
    result: TokenPairDto = await command_bus.execute(
        RefreshTokenCommand(refresh_token=body.refresh_token)
    )
    return _to_response(result)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
@inject
async def logout(
    body: LogoutRequest,
    command_bus: CommandBus = Depends(Provide[Container.command_bus]),
) -> None:
    await command_bus.execute(LogoutCommand(refresh_token=body.refresh_token))
