"""Authentication HTTP routes — Login / Logout / Refresh."""

from __future__ import annotations

from typing import Any

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
    clear_refresh_cookie,
    read_refresh_cookie,
    set_refresh_cookie,
)
from src.modules.authentication.routes.schemas import (
    LoginRequest,
    LogoutRequest,
    MeResponse,
    RefreshRequest,
    TokenResponse,
)
from src.modules.services.service import ServiceCatalogService
from src.shared.application.command_bus import CommandBus
from src.shared.infrastructure.di.container import Container
from src.shared.infrastructure.exceptions import UnauthorizedError
from src.shared.infrastructure.security.current_user import CurrentUser
from src.shared.infrastructure.security.dependencies import get_current_user
from src.shared.infrastructure.security.entitlements import entitled_services

router = APIRouter(prefix="/auth", tags=["authentication"])


def _to_response(dto: TokenPairDto) -> TokenResponse:
    return TokenResponse(
        access_token=dto.access_token,
        token_type=dto.token_type,
        expires_in=dto.expires_in,
        user_id=dto.user_id,
        email=dto.email,
        full_name=dto.full_name,
        mfa_required=dto.mfa_required,
        mfa_token=dto.mfa_token,
    )


def _refresh_token_from_request(request: Request, body_token: str | None) -> str:
    token = (body_token or "").strip() or read_refresh_cookie(request)
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
    if not result.mfa_required:
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


@router.get("/me", response_model=MeResponse)
@inject
async def me(
    actor: CurrentUser = Depends(get_current_user),
    uow_factory: Any = Depends(Provide[Container.unit_of_work]),
    catalog: ServiceCatalogService = Depends(Provide[Container.service_catalog]),
) -> MeResponse:
    """Identity, effective permissions and entitled services for the SPA."""
    async with uow_factory:
        contracted = await catalog.entitled_namespaces(actor.tenant_id)
    return MeResponse(
        id=actor.id,
        email=actor.email,
        full_name=actor.full_name,
        tenant_id=actor.tenant_id,
        tenant_slug=actor.tenant_slug,
        tenant_name=actor.tenant_name,
        role_names=sorted(actor.role_names),
        permissions=sorted(actor.permissions),
        services=sorted(entitled_services(actor.permissions, contracted)),
    )


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
