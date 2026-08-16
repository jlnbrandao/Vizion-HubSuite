from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dataclasses import replace

from openvizion.kernel.identity import Principal

from tracking.domain.errors import UnauthorizedError
from tracking.infrastructure.composition import AppContainer, load_principal_from_user_row
from tracking.infrastructure.database.models import UserModel
from tracking.infrastructure.security.jwt import permissions_for_role
from tracking.infrastructure.security.passwords import verify_password
from tracking.infrastructure.security.tenant import require_tenant
from tracking.interfaces.api.deps import get_container, get_current_user, get_session

router = APIRouter(prefix="/auth", tags=["authentication"])


class LoginRequest(BaseModel):
    login: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: str
    email: str
    full_name: str


class MeResponse(BaseModel):
    id: str
    email: str
    full_name: str
    tenant_id: str
    tenant_slug: str
    tenant_name: str
    role_names: list[str]
    permissions: list[str]
    services: list[str] = Field(default_factory=list)


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    container: AppContainer = Depends(get_container),
) -> TokenResponse:
    tenant = require_tenant()
    principal: Principal
    if container.hub is not None:
        host = request.headers.get("host") or f"{tenant.slug}.localhost"
        try:
            data = await container.hub.login(
                login=body.login.strip(),
                password=body.password,
                tenant_host=host,
            )
        except PermissionError as exc:
            raise UnauthorizedError("Invalid credentials") from exc
        hub_token = data["access_token"]
        principal = await container.hub.get_current_user(hub_token)
        if principal.has_role("PLATFORM") or principal.has_role("ADMIN"):
            role = "ADMIN"
        elif principal.has_role("MANAGER") or principal.has_role("OPERATOR"):
            role = "OPERATOR"
        else:
            role = "VIEWER"
        principal = replace(
            principal,
            role_names=frozenset({role}),
            permissions=permissions_for_role(role),
        )
    else:
        ident = body.login.strip().lower()
        result = await session.execute(
            select(UserModel).where(
                UserModel.tenant_id == tenant.id,
                UserModel.email == ident,
                UserModel.is_active.is_(True),
            )
        )
        row = result.scalar_one_or_none()
        if row is None or not verify_password(body.password, row.hashed_password):
            raise UnauthorizedError("Invalid credentials")
        principal = await load_principal_from_user_row(row, tenant)

    token = container.jwt.create_access_token(principal)
    await container.platform.audit(action="auth.login", principal=principal)
    return TokenResponse(
        access_token=token,
        expires_in=container.settings.jwt_access_token_expire_minutes * 60,
        user_id=str(principal.id),
        email=principal.email,
        full_name=principal.full_name,
    )


@router.get("/me", response_model=MeResponse)
async def me(
    principal: Principal = Depends(get_current_user),
    container: AppContainer = Depends(get_container),
) -> MeResponse:
    caps = await container.entitlements.list_for_tenant(principal.tenant_id)
    return MeResponse(
        id=str(principal.id),
        email=principal.email,
        full_name=principal.full_name,
        tenant_id=str(principal.tenant_id),
        tenant_slug=principal.tenant_slug,
        tenant_name=principal.tenant_name,
        role_names=sorted(principal.role_names),
        permissions=sorted(principal.permissions),
        services=["tracking", *sorted(caps)],
    )


@router.post("/logout")
async def logout(principal: Principal = Depends(get_current_user)) -> dict[str, str]:
    return {"status": "ok"}
