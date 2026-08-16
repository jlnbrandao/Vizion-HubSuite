from __future__ import annotations

from fastapi import Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from openvizion.kernel.identity import Principal

from tracking.domain.errors import ForbiddenError, UnauthorizedError
from tracking.infrastructure.composition import AppContainer
from tracking.permissions import CAPABILITY_BASIC
from tracking.infrastructure.repositories.sql import (
    SqlDeviceRepository,
    SqlGeofenceRepository,
    SqlPositionRepository,
    SqlVehicleRepository,
)
from tracking.infrastructure.security.jwt import JwtService
from tracking.infrastructure.security.tenant import require_tenant


def get_container(request: Request) -> AppContainer:
    return request.app.state.container


async def get_session(request: Request) -> AsyncSession:
    container: AppContainer = request.app.state.container
    async with container.session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_jwt(request: Request) -> JwtService:
    return request.app.state.container.jwt


async def get_current_user(
    request: Request,
    authorization: str | None = Header(default=None),
    jwt: JwtService = Depends(get_jwt),
) -> Principal:
    if not authorization:
        raise UnauthorizedError("Missing Authorization header")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise UnauthorizedError("Invalid Authorization header")
    principal = jwt.decode(token.strip())
    tenant = require_tenant()
    if principal.tenant_id != tenant.id:
        raise UnauthorizedError("Token tenant does not match Host tenant")
    return principal


def require_permission(code: str):
    async def _dep(
        request: Request,
        principal: Principal = Depends(get_current_user),
    ) -> Principal:
        container: AppContainer = request.app.state.container
        decision = await container.authorization.authorize(principal, code)
        if not decision.allowed:
            raise ForbiddenError("Insufficient permissions")
        if container.hub is not None:
            entitled = await container.entitlements.has(principal.tenant_id, "tracking")
            if not entitled:
                entitled = await container.entitlements.has(principal.tenant_id, CAPABILITY_BASIC)
            if not entitled:
                raise ForbiddenError("Tenant is not entitled to tracking")
        return principal

    return _dep


def devices_repo(session: AsyncSession = Depends(get_session)) -> SqlDeviceRepository:
    return SqlDeviceRepository(session)


def vehicles_repo(session: AsyncSession = Depends(get_session)) -> SqlVehicleRepository:
    return SqlVehicleRepository(session)


def positions_repo(session: AsyncSession = Depends(get_session)) -> SqlPositionRepository:
    return SqlPositionRepository(session)


def geofences_repo(session: AsyncSession = Depends(get_session)) -> SqlGeofenceRepository:
    return SqlGeofenceRepository(session)
