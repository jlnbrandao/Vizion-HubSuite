"""IAM HTTP routes — audit, sessions, lifecycle, MFA, OAuth, machine, federation, ABAC."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from uuid import UUID

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Form, Query, Request, Response, status
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, EmailStr, Field

from src.config.settings import Settings
from src.modules.authentication.dtos.auth_dtos import RefreshSessionDto, TokenPairDto
from src.modules.authentication.routes.auth_cookies import set_refresh_cookie
from src.modules.authentication.services.refresh_token_store import RefreshTokenStore
from src.modules.authentication.services.token_service import TokenService
from src.modules.authentication.value_objects.access_token_claims import AccessTokenClaims
from src.modules.authentication.value_objects.refresh_token import RefreshToken
from src.modules.iam.abac.service import AbacService
from src.modules.iam.acl.service import AclService
from src.modules.iam.audit.service import AuditService
from src.modules.iam.federation.service import FederationService
from src.modules.iam.lifecycle.service import LifecycleService
from src.modules.iam.machine.service import MachineIdentityService
from src.modules.iam.mfa.service import MfaService
from src.modules.iam.oauth.service import OAuthService, OidcKeyStore
from src.modules.iam.policies.service import AuthPolicyService
from src.modules.iam.sessions.service import SessionService
from src.modules.users.queries.user_queries import GetUserByIdQuery
from src.shared.application.query_bus import QueryBus
from src.shared.infrastructure.di.container import Container
from src.shared.infrastructure.exceptions import NotFoundError
from src.shared.infrastructure.security.current_user import CurrentUser
from src.shared.infrastructure.security.dependencies import get_current_user, require_permission
from src.shared.infrastructure.security.permission_codes import PermissionCode
from src.shared.infrastructure.security.session_denylist import SessionDenylist
from src.shared.infrastructure.tenant_context import (
    get_current_tenant_slug,
    require_current_tenant_id,
)

router = APIRouter(tags=["iam"])


# ---------- schemas ----------


class InviteRequest(BaseModel):
    email: EmailStr
    username: str
    full_name: str
    role_ids: list[UUID] = Field(default_factory=list)


class AcceptInvitationRequest(BaseModel):
    token: str
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class AuthPolicyUpdate(BaseModel):
    max_failed_attempts: int | None = None
    lockout_minutes: int | None = None
    password_min_age_hours: int | None = None
    password_max_age_days: int | None = None
    password_history_count: int | None = None
    session_idle_minutes: int | None = None
    mfa_required: str | None = None
    allowed_amr: list[str] | None = None
    ip_allowlist: list[str] | None = None
    password_login_enabled: bool | None = None
    jit_provisioning_enabled: bool | None = None


class MfaConfirmRequest(BaseModel):
    method_id: UUID
    code: str


class MfaVerifyRequest(BaseModel):
    mfa_token: str
    code: str | None = None
    credential_id: str | None = None


class OAuthClientCreate(BaseModel):
    name: str
    redirect_uris: list[str]
    grant_types: list[str] | None = None
    is_confidential: bool = True
    service_account_id: UUID | None = None


class ConsentRequest(BaseModel):
    client_id: str
    scopes: list[str]
    redirect_uri: str
    code_challenge: str | None = None
    code_challenge_method: str | None = "S256"
    state: str | None = None


class ServiceAccountCreate(BaseModel):
    name: str
    description: str = ""
    role_ids: list[UUID] = Field(default_factory=list)


class ApiKeyCreate(BaseModel):
    service_account_id: UUID
    name: str
    scopes: list[str] = Field(default_factory=list)


class IdpCreate(BaseModel):
    name: str
    provider_type: str
    client_id: str | None = None
    client_secret: str | None = None
    issuer: str | None = None
    metadata_url: str | None = None
    attribute_mapping: dict[str, Any] | None = None


class IdpUpdate(BaseModel):
    name: str | None = None
    client_id: str | None = None
    client_secret: str | None = None
    issuer: str | None = None
    metadata_url: str | None = None
    attribute_mapping: dict[str, Any] | None = None
    enabled: bool | None = None


class PolicyCreate(BaseModel):
    name: str
    description: str = ""
    effect: str = "allow"
    actions: list[str] = Field(default_factory=list)
    resource_types: list[str] = Field(default_factory=list)
    conditions: dict[str, Any] = Field(default_factory=dict)
    priority: int = 100


class AclGrant(BaseModel):
    subject_type: Literal["user", "role"]
    subject_id: UUID
    resource_type: str = Field(min_length=1, max_length=64)
    resource_id: str = Field(min_length=1, max_length=64)
    action: str = Field(min_length=1, max_length=120)
    effect: Literal["allow", "deny"] = "allow"
    expires_at: datetime | None = None


# ---------- helpers ----------


async def _issue_session_tokens(
    *,
    user_id: UUID,
    email: str,
    full_name: str,
    role_ids: tuple[UUID, ...],
    credentials_version: int,
    amr: tuple[str, ...],
    token_service: TokenService,
    refresh_store: RefreshTokenStore,
    sessions: SessionService,
    settings: Settings,
    ip: str | None = None,
    ua: str | None = None,
) -> TokenPairDto:
    tenant_id = require_current_tenant_id()
    tenant_slug = get_current_tenant_slug() or ""
    expires_at = datetime.now(UTC) + timedelta(days=settings.jwt_refresh_token_expire_days)
    session_id = await sessions.create(
        user_id=user_id,
        amr=amr,
        ip_address=ip,
        user_agent=ua,
        expires_at=expires_at,
    )
    claims = AccessTokenClaims(
        user_id=user_id,
        tenant_id=tenant_id,
        tenant_slug=tenant_slug,
        credentials_version=credentials_version,
        amr=amr,
        acr="mfa" if any(x in amr for x in ("otp", "pop", "rck")) else "pwd",
        sid=session_id,
    )
    access = token_service.create_access_token(claims)
    refresh = RefreshToken.generate()
    await refresh_store.save(
        refresh,
        RefreshSessionDto(
            user_id=user_id,
            email=email,
            full_name=full_name,
            tenant_id=tenant_id,
            tenant_slug=tenant_slug,
            role_ids=role_ids,
            created_at=datetime.now(UTC),
            session_id=session_id,
            amr=amr,
        ),
    )
    return TokenPairDto(
        access_token=access,
        refresh_token=refresh.value,
        expires_in=token_service.access_token_expires_in_seconds(),
        user_id=user_id,
        email=email,
        full_name=full_name,
    )


# ---------- audit / sessions ----------


@router.get("/audit-events")
@inject
async def list_audit_events(
    action: str | None = None,
    request_id: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _: CurrentUser = Depends(require_permission(PermissionCode.AUDIT_READ)),
    uow_factory: Any = Depends(Provide[Container.unit_of_work]),
    audit: AuditService = Depends(Provide[Container.audit_service]),
) -> list[dict[str, Any]]:
    async with uow_factory as uow:
        rows = await audit.list_events(
            action=action, request_id=request_id, limit=limit, offset=offset
        )
        await uow.commit()
        return [
            {
                "id": str(r.id),
                "action": r.action,
                "actor_user_id": str(r.actor_user_id) if r.actor_user_id else None,
                "actor_type": r.actor_type,
                "resource_type": r.resource_type,
                "resource_id": r.resource_id,
                "request_id": r.request_id,
                "payload": r.payload,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]


@router.get("/sessions")
@inject
async def list_my_sessions(
    actor: CurrentUser = Depends(get_current_user),
    uow_factory: Any = Depends(Provide[Container.unit_of_work]),
    sessions: SessionService = Depends(Provide[Container.session_service]),
) -> list[dict[str, Any]]:
    async with uow_factory as uow:
        rows = await sessions.list_for_user(actor.id)
        await uow.commit()
        return [
            {
                "id": str(r.id),
                "amr": r.amr,
                "ip_address": r.ip_address,
                "user_agent": r.user_agent,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "expires_at": r.expires_at.isoformat() if r.expires_at else None,
                "revoked_at": r.revoked_at.isoformat() if r.revoked_at else None,
            }
            for r in rows
        ]


@router.post("/sessions/{session_id}/revoke", status_code=204)
@inject
async def revoke_my_session(
    session_id: UUID,
    actor: CurrentUser = Depends(get_current_user),
    uow_factory: Any = Depends(Provide[Container.unit_of_work]),
    sessions: SessionService = Depends(Provide[Container.session_service]),
    denylist: SessionDenylist = Depends(Provide[Container.session_denylist]),
) -> None:
    async with uow_factory as uow:
        revoked = await sessions.revoke(session_id, actor.id)
        await uow.commit()
    if not revoked:
        raise NotFoundError("Session not found")
    await denylist.revoke(session_id)


@router.post("/sessions/revoke-all", status_code=204)
@inject
async def revoke_my_sessions(
    actor: CurrentUser = Depends(get_current_user),
    uow_factory: Any = Depends(Provide[Container.unit_of_work]),
    sessions: SessionService = Depends(Provide[Container.session_service]),
    refresh_store: RefreshTokenStore = Depends(Provide[Container.refresh_token_store]),
    denylist: SessionDenylist = Depends(Provide[Container.session_denylist]),
) -> None:
    async with uow_factory as uow:
        revoked_ids = await sessions.revoke_all_for_user(actor.id)
        await refresh_store.delete_all_for_user(actor.id)
        await uow.commit()
    await denylist.revoke_many(revoked_ids)


@router.post("/users/{user_id}/sessions/revoke", status_code=204)
@inject
async def revoke_user_sessions(
    user_id: UUID,
    _: CurrentUser = Depends(require_permission(PermissionCode.SESSIONS_REVOKE)),
    uow_factory: Any = Depends(Provide[Container.unit_of_work]),
    sessions: SessionService = Depends(Provide[Container.session_service]),
    refresh_store: RefreshTokenStore = Depends(Provide[Container.refresh_token_store]),
    denylist: SessionDenylist = Depends(Provide[Container.session_denylist]),
) -> None:
    async with uow_factory as uow:
        revoked_ids = await sessions.revoke_all_for_user(user_id)
        await refresh_store.delete_all_for_user(user_id)
        await uow.commit()
    await denylist.revoke_many(revoked_ids)


# ---------- lifecycle / policies ----------


@router.post("/invitations")
@inject
async def create_invitation(
    body: InviteRequest,
    actor: CurrentUser = Depends(require_permission(PermissionCode.USERS_CREATE)),
    uow_factory: Any = Depends(Provide[Container.unit_of_work]),
    lifecycle: LifecycleService = Depends(Provide[Container.lifecycle_service]),
) -> dict[str, Any]:
    async with uow_factory as uow:
        model, raw = await lifecycle.create_invitation(
            email=body.email,
            username=body.username,
            full_name=body.full_name,
            role_ids=body.role_ids,
            invited_by=actor.id,
        )
        await uow.commit()
        return {"id": str(model.id), "email": model.email, "token": raw}


@router.post("/auth/accept-invitation")
@inject
async def accept_invitation(
    body: AcceptInvitationRequest,
    uow_factory: Any = Depends(Provide[Container.unit_of_work]),
    lifecycle: LifecycleService = Depends(Provide[Container.lifecycle_service]),
) -> dict[str, str]:
    async with uow_factory as uow:
        user_id = await lifecycle.accept_invitation(token=body.token, password=body.password)
        await uow.commit()
        return {"user_id": str(user_id)}


@router.post("/auth/forgot-password", status_code=204)
@inject
async def forgot_password(
    body: ForgotPasswordRequest,
    uow_factory: Any = Depends(Provide[Container.unit_of_work]),
    lifecycle: LifecycleService = Depends(Provide[Container.lifecycle_service]),
) -> None:
    async with uow_factory as uow:
        await lifecycle.forgot_password(email=body.email)
        await uow.commit()


@router.post("/auth/reset-password", status_code=204)
@inject
async def reset_password(
    body: ResetPasswordRequest,
    uow_factory: Any = Depends(Provide[Container.unit_of_work]),
    lifecycle: LifecycleService = Depends(Provide[Container.lifecycle_service]),
) -> None:
    async with uow_factory as uow:
        await lifecycle.reset_password(token=body.token, new_password=body.new_password)
        await uow.commit()


@router.get("/auth-policies")
@inject
async def get_auth_policy(
    _: CurrentUser = Depends(require_permission(PermissionCode.POLICIES_READ)),
    uow_factory: Any = Depends(Provide[Container.unit_of_work]),
    policies: AuthPolicyService = Depends(Provide[Container.auth_policy_service]),
) -> dict[str, Any]:
    async with uow_factory as uow:
        p = await policies.get_or_create()
        await uow.commit()
        return {
            "max_failed_attempts": p.max_failed_attempts,
            "lockout_minutes": p.lockout_minutes,
            "password_min_age_hours": p.password_min_age_hours,
            "password_max_age_days": p.password_max_age_days,
            "password_history_count": p.password_history_count,
            "session_idle_minutes": p.session_idle_minutes,
            "mfa_required": p.mfa_required,
            "allowed_amr": p.allowed_amr,
            "ip_allowlist": p.ip_allowlist,
            "password_login_enabled": p.password_login_enabled,
            "jit_provisioning_enabled": p.jit_provisioning_enabled,
        }


@router.put("/auth-policies")
@inject
async def update_auth_policy(
    body: AuthPolicyUpdate,
    _: CurrentUser = Depends(require_permission(PermissionCode.POLICIES_UPDATE)),
    uow_factory: Any = Depends(Provide[Container.unit_of_work]),
    policies: AuthPolicyService = Depends(Provide[Container.auth_policy_service]),
) -> dict[str, Any]:
    async with uow_factory as uow:
        p = await policies.update(**body.model_dump(exclude_none=True))
        await uow.commit()
        return {"mfa_required": p.mfa_required, "max_failed_attempts": p.max_failed_attempts}


# ---------- MFA ----------


@router.post("/auth/mfa/totp/enroll")
@inject
async def enroll_totp(
    actor: CurrentUser = Depends(get_current_user),
    uow_factory: Any = Depends(Provide[Container.unit_of_work]),
    mfa: MfaService = Depends(Provide[Container.mfa_service]),
) -> dict[str, str]:
    async with uow_factory as uow:
        data = await mfa.start_totp_enroll(actor.id, actor.email)
        await uow.commit()
        return data


@router.post("/auth/mfa/totp/confirm")
@inject
async def confirm_totp(
    body: MfaConfirmRequest,
    actor: CurrentUser = Depends(get_current_user),
    uow_factory: Any = Depends(Provide[Container.unit_of_work]),
    mfa: MfaService = Depends(Provide[Container.mfa_service]),
) -> dict[str, Any]:
    async with uow_factory as uow:
        codes = await mfa.confirm_totp(user_id=actor.id, method_id=body.method_id, code=body.code)
        await uow.commit()
        return {"recovery_codes": codes}


@router.post("/auth/mfa/verify")
@inject
async def verify_mfa(
    body: MfaVerifyRequest,
    response: Response,
    request: Request,
    uow_factory: Any = Depends(Provide[Container.unit_of_work]),
    mfa: MfaService = Depends(Provide[Container.mfa_service]),
    query_bus: QueryBus = Depends(Provide[Container.query_bus]),
    token_service: TokenService = Depends(Provide[Container.token_service]),
    refresh_store: RefreshTokenStore = Depends(Provide[Container.refresh_token_store]),
    sessions: SessionService = Depends(Provide[Container.session_service]),
    settings: Settings = Depends(Provide[Container.config]),
) -> dict[str, Any]:
    user_id, _tenant_id = mfa.decode_mfa_token(body.mfa_token)
    async with uow_factory as uow:
        if body.credential_id:
            amr_method = await mfa.complete_webauthn_authentication(
                user_id=user_id, credential_id=body.credential_id
            )
        else:
            amr_method = await mfa.verify_totp_or_recovery(
                user_id=user_id, code=body.code or ""
            )
        user = await query_bus.ask(GetUserByIdQuery(user_id=user_id))
        pair = await _issue_session_tokens(
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
            role_ids=user.role_ids,
            credentials_version=user.credentials_version,
            amr=("pwd", amr_method),
            token_service=token_service,
            refresh_store=refresh_store,
            sessions=sessions,
            settings=settings,
            ip=request.client.host if request.client else None,
            ua=request.headers.get("user-agent"),
        )
        await uow.commit()
    set_refresh_cookie(response, pair.refresh_token, settings)
    return {
        "access_token": pair.access_token,
        "token_type": "bearer",
        "expires_in": pair.expires_in,
        "user_id": str(pair.user_id),
        "email": pair.email,
        "full_name": pair.full_name,
    }


@router.post("/auth/mfa/webauthn/register/begin")
@inject
async def webauthn_register_begin(
    actor: CurrentUser = Depends(get_current_user),
    uow_factory: Any = Depends(Provide[Container.unit_of_work]),
    mfa: MfaService = Depends(Provide[Container.mfa_service]),
) -> dict[str, Any]:
    async with uow_factory as uow:
        data = await mfa.begin_webauthn_registration(actor.id, actor.email)
        await uow.commit()
        return data


@router.post("/auth/mfa/webauthn/register/complete", status_code=204)
@inject
async def webauthn_register_complete(
    body: dict[str, str],
    actor: CurrentUser = Depends(get_current_user),
    uow_factory: Any = Depends(Provide[Container.unit_of_work]),
    mfa: MfaService = Depends(Provide[Container.mfa_service]),
) -> None:
    async with uow_factory as uow:
        await mfa.complete_webauthn_registration(
            user_id=actor.id,
            method_id=UUID(body["method_id"]),
            credential_id=body["credential_id"],
            public_key=body.get("public_key", ""),
        )
        await uow.commit()


# ---------- OAuth / OIDC ----------


@router.get("/.well-known/openid-configuration")
@inject
async def openid_configuration(
    oauth: OAuthService = Depends(Provide[Container.oauth_service]),
) -> dict[str, Any]:
    return oauth.discovery_document()


@router.get("/jwks.json")
@inject
async def jwks(
    keys: OidcKeyStore = Depends(Provide[Container.oidc_key_store]),
) -> dict[str, Any]:
    return keys.jwks()


@router.get("/oauth/clients")
@inject
async def list_oauth_clients(
    _: CurrentUser = Depends(require_permission(PermissionCode.OAUTH_CLIENTS_READ)),
    uow_factory: Any = Depends(Provide[Container.unit_of_work]),
    oauth: OAuthService = Depends(Provide[Container.oauth_service]),
) -> list[dict[str, Any]]:
    async with uow_factory as uow:
        await oauth.ensure_default_scopes()
        clients = await oauth.list_clients()
        await uow.commit()
        return [
            {
                "client_id": c.client_id,
                "name": c.name,
                "redirect_uris": c.redirect_uris,
                "grant_types": c.grant_types,
                "is_confidential": c.is_confidential,
            }
            for c in clients
        ]


@router.post("/oauth/clients")
@inject
async def create_oauth_client(
    body: OAuthClientCreate,
    _: CurrentUser = Depends(require_permission(PermissionCode.OAUTH_CLIENTS_CREATE)),
    uow_factory: Any = Depends(Provide[Container.unit_of_work]),
    oauth: OAuthService = Depends(Provide[Container.oauth_service]),
) -> dict[str, Any]:
    async with uow_factory as uow:
        client, secret = await oauth.create_client(
            name=body.name,
            redirect_uris=body.redirect_uris,
            grant_types=body.grant_types,
            is_confidential=body.is_confidential,
            service_account_id=body.service_account_id,
        )
        await uow.commit()
        return {
            "client_id": client.client_id,
            "client_secret": secret,
            "name": client.name,
        }


@router.delete("/oauth/clients/{client_id}", status_code=204)
@inject
async def delete_oauth_client(
    client_id: str,
    _: CurrentUser = Depends(require_permission(PermissionCode.OAUTH_CLIENTS_DELETE)),
    uow_factory: Any = Depends(Provide[Container.unit_of_work]),
    oauth: OAuthService = Depends(Provide[Container.oauth_service]),
) -> None:
    async with uow_factory as uow:
        await oauth.delete_client(client_id)
        await uow.commit()


@router.post("/oauth/consent")
@inject
async def oauth_consent(
    body: ConsentRequest,
    actor: CurrentUser = Depends(require_permission(PermissionCode.USERS_READ)),
    uow_factory: Any = Depends(Provide[Container.unit_of_work]),
    oauth: OAuthService = Depends(Provide[Container.oauth_service]),
) -> dict[str, str]:
    async with uow_factory as uow:
        await oauth.grant_consent(
            user_id=actor.id, client_id=body.client_id, scopes=body.scopes
        )
        code = await oauth.create_authorization_code(
            client_id=body.client_id,
            user_id=actor.id,
            redirect_uri=body.redirect_uri,
            scopes=body.scopes,
            code_challenge=body.code_challenge,
            code_challenge_method=body.code_challenge_method,
        )
        await uow.commit()
    redirect = f"{body.redirect_uri}?code={code}"
    if body.state:
        redirect += f"&state={body.state}"
    return {"redirect_to": redirect, "code": code}


@router.post("/oauth/token")
@inject
async def oauth_token(
    grant_type: str = Form(...),
    code: str | None = Form(None),
    redirect_uri: str | None = Form(None),
    client_id: str = Form(...),
    client_secret: str | None = Form(None),
    code_verifier: str | None = Form(None),
    scope: str | None = Form(None),
    uow_factory: Any = Depends(Provide[Container.unit_of_work]),
    oauth: OAuthService = Depends(Provide[Container.oauth_service]),
) -> dict[str, Any]:
    async with uow_factory as uow:
        if grant_type == "authorization_code":
            result = await oauth.exchange_code(
                code=code or "",
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri or "",
                code_verifier=code_verifier,
            )
        elif grant_type == "client_credentials":
            result = await oauth.client_credentials(
                client_id=client_id,
                client_secret=client_secret or "",
                scopes=(scope or "").split(),
            )
        else:
            return JSONResponse(
                status_code=400, content={"error": "unsupported_grant_type"}
            )
        await uow.commit()
        return result


@router.get("/oauth/userinfo")
async def oauth_userinfo(
    actor: CurrentUser = Depends(require_permission(PermissionCode.USERS_READ)),
) -> dict[str, Any]:
    return {
        "sub": str(actor.id),
        "email": actor.email,
        "name": actor.full_name,
    }


# ---------- machine identities ----------


@router.get("/service-accounts")
@inject
async def list_service_accounts(
    _: CurrentUser = Depends(require_permission(PermissionCode.SERVICE_ACCOUNTS_READ)),
    uow_factory: Any = Depends(Provide[Container.unit_of_work]),
    machine: MachineIdentityService = Depends(Provide[Container.machine_identity_service]),
) -> list[dict[str, Any]]:
    async with uow_factory as uow:
        rows = await machine.list_service_accounts()
        await uow.commit()
        return [
            {
                "id": str(r.id),
                "name": r.name,
                "description": r.description,
                "role_ids": [str(x) for x in r.role_ids],
                "is_active": r.is_active,
            }
            for r in rows
        ]


@router.post("/service-accounts")
@inject
async def create_service_account(
    body: ServiceAccountCreate,
    _: CurrentUser = Depends(require_permission(PermissionCode.SERVICE_ACCOUNTS_CREATE)),
    uow_factory: Any = Depends(Provide[Container.unit_of_work]),
    machine: MachineIdentityService = Depends(Provide[Container.machine_identity_service]),
) -> dict[str, Any]:
    async with uow_factory as uow:
        row = await machine.create_service_account(
            name=body.name, description=body.description, role_ids=body.role_ids
        )
        await uow.commit()
        return {"id": str(row.id), "name": row.name}


@router.post("/api-keys")
@inject
async def create_api_key(
    body: ApiKeyCreate,
    _: CurrentUser = Depends(require_permission(PermissionCode.API_KEYS_CREATE)),
    uow_factory: Any = Depends(Provide[Container.unit_of_work]),
    machine: MachineIdentityService = Depends(Provide[Container.machine_identity_service]),
) -> dict[str, Any]:
    async with uow_factory as uow:
        key, raw = await machine.create_api_key(
            service_account_id=body.service_account_id,
            name=body.name,
            scopes=body.scopes,
        )
        await uow.commit()
        return {
            "id": str(key.id),
            "prefix": key.prefix,
            "api_key": raw,
            "name": key.name,
        }


@router.get("/api-keys")
@inject
async def list_api_keys(
    service_account_id: UUID | None = None,
    _: CurrentUser = Depends(require_permission(PermissionCode.API_KEYS_READ)),
    uow_factory: Any = Depends(Provide[Container.unit_of_work]),
    machine: MachineIdentityService = Depends(Provide[Container.machine_identity_service]),
) -> list[dict[str, Any]]:
    async with uow_factory as uow:
        rows = await machine.list_api_keys(service_account_id)
        await uow.commit()
        return [
            {
                "id": str(r.id),
                "name": r.name,
                "prefix": r.prefix,
                "scopes": r.scopes,
                "service_account_id": str(r.service_account_id),
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "last_used_at": r.last_used_at.isoformat() if r.last_used_at else None,
                "expires_at": r.expires_at.isoformat() if r.expires_at else None,
                "revoked_at": r.revoked_at.isoformat() if r.revoked_at else None,
            }
            for r in rows
        ]


@router.delete("/api-keys/{key_id}", status_code=204)
@inject
async def revoke_api_key(
    key_id: UUID,
    _: CurrentUser = Depends(require_permission(PermissionCode.API_KEYS_DELETE)),
    uow_factory: Any = Depends(Provide[Container.unit_of_work]),
    machine: MachineIdentityService = Depends(Provide[Container.machine_identity_service]),
) -> None:
    async with uow_factory as uow:
        await machine.revoke_api_key(key_id)
        await uow.commit()


# ---------- federation ----------


@router.get("/auth/sso/providers")
@inject
async def public_sso_providers(
    uow_factory: Any = Depends(Provide[Container.unit_of_work]),
    federation: FederationService = Depends(Provide[Container.federation_service]),
) -> list[dict[str, Any]]:
    async with uow_factory as uow:
        rows = await federation.list_providers(enabled_only=True)
        await uow.commit()
        return [
            {"id": str(r.id), "name": r.name, "provider_type": r.provider_type}
            for r in rows
        ]


def _idp_to_dict(row: Any) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "name": row.name,
        "provider_type": row.provider_type,
        "client_id": row.client_id,
        "issuer": row.issuer,
        "metadata_url": row.metadata_url,
        "attribute_mapping": row.attribute_mapping or {},
        "enabled": row.enabled,
        "has_client_secret": bool(row.client_secret_encrypted),
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


@router.get("/identity-providers")
@inject
async def list_idps(
    _: CurrentUser = Depends(require_permission(PermissionCode.FEDERATION_READ)),
    uow_factory: Any = Depends(Provide[Container.unit_of_work]),
    federation: FederationService = Depends(Provide[Container.federation_service]),
) -> list[dict[str, Any]]:
    async with uow_factory as uow:
        rows = await federation.list_providers()
        await uow.commit()
        return [_idp_to_dict(r) for r in rows]


@router.post("/identity-providers", status_code=status.HTTP_201_CREATED)
@inject
async def create_idp(
    body: IdpCreate,
    _: CurrentUser = Depends(require_permission(PermissionCode.FEDERATION_CREATE)),
    uow_factory: Any = Depends(Provide[Container.unit_of_work]),
    federation: FederationService = Depends(Provide[Container.federation_service]),
) -> dict[str, Any]:
    async with uow_factory as uow:
        row = await federation.create_provider(**body.model_dump())
        await uow.commit()
        return _idp_to_dict(row)


@router.patch("/identity-providers/{provider_id}")
@inject
async def update_idp(
    provider_id: UUID,
    body: IdpUpdate,
    _: CurrentUser = Depends(require_permission(PermissionCode.FEDERATION_UPDATE)),
    uow_factory: Any = Depends(Provide[Container.unit_of_work]),
    federation: FederationService = Depends(Provide[Container.federation_service]),
) -> dict[str, Any]:
    payload = body.model_dump(exclude_unset=True)
    if "client_secret" in payload:
        secret = payload.pop("client_secret")
        if secret is not None and str(secret).strip():
            payload["client_secret_encrypted"] = str(secret).strip()
    async with uow_factory as uow:
        row = await federation.update_provider(provider_id, **payload)
        await uow.commit()
        return _idp_to_dict(row)


@router.delete("/identity-providers/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
@inject
async def delete_idp(
    provider_id: UUID,
    _: CurrentUser = Depends(require_permission(PermissionCode.FEDERATION_DELETE)),
    uow_factory: Any = Depends(Provide[Container.unit_of_work]),
    federation: FederationService = Depends(Provide[Container.federation_service]),
) -> None:
    async with uow_factory as uow:
        await federation.delete_provider(provider_id)
        await uow.commit()


@router.get("/auth/sso/{provider_id}/start")
@inject
async def sso_start(
    provider_id: UUID,
    redirect_uri: str = Query(...),
    uow_factory: Any = Depends(Provide[Container.unit_of_work]),
    federation: FederationService = Depends(Provide[Container.federation_service]),
) -> RedirectResponse:
    async with uow_factory as uow:
        provider = await federation.get_provider(provider_id)
        state = str(provider_id)
        if provider.provider_type == "oidc":
            url = federation.build_oidc_authorize_url(
                provider, redirect_uri=redirect_uri, state=state
            )
        else:
            url = redirect_uri
        await uow.commit()
    return RedirectResponse(url)


@router.post("/auth/sso/saml/acs")
@inject
async def saml_acs(
    provider_id: UUID = Form(...),
    SAMLResponse: str = Form(...),
    uow_factory: Any = Depends(Provide[Container.unit_of_work]),
    federation: FederationService = Depends(Provide[Container.federation_service]),
    policies: AuthPolicyService = Depends(Provide[Container.auth_policy_service]),
) -> dict[str, str]:
    async with uow_factory as uow:
        data = federation.parse_saml_response_stub(SAMLResponse)
        policy = await policies.get_or_create()
        email = data.get("email") or data["name_id"]
        user_id = await federation.link_or_provision(
            provider_id=provider_id,
            external_subject=data.get("name_id", email),
            email=email,
            full_name=data.get("full_name", email),
            jit=policy.jit_provisioning_enabled,
        )
        await uow.commit()
        return {"user_id": str(user_id)}


# ---------- ABAC ----------


@router.get("/access-policies")
@inject
async def list_access_policies(
    _: CurrentUser = Depends(require_permission(PermissionCode.POLICIES_READ)),
    uow_factory: Any = Depends(Provide[Container.unit_of_work]),
    abac: AbacService = Depends(Provide[Container.abac_service]),
) -> list[dict[str, Any]]:
    async with uow_factory as uow:
        rows = await abac.list_policies()
        await uow.commit()
        return [
            {
                "id": str(r.id),
                "name": r.name,
                "effect": r.effect,
                "actions": r.actions,
                "conditions": r.conditions,
                "priority": r.priority,
                "is_active": r.is_active,
            }
            for r in rows
        ]


@router.post("/access-policies")
@inject
async def create_access_policy(
    body: PolicyCreate,
    _: CurrentUser = Depends(require_permission(PermissionCode.POLICIES_CREATE)),
    uow_factory: Any = Depends(Provide[Container.unit_of_work]),
    abac: AbacService = Depends(Provide[Container.abac_service]),
) -> dict[str, Any]:
    async with uow_factory as uow:
        row = await abac.create_policy(**body.model_dump())
        await uow.commit()
        return {"id": str(row.id), "name": row.name}


# ---------- ACL ----------


def _acl_to_dict(row: Any) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "subject_type": row.subject_type,
        "subject_id": str(row.subject_id),
        "resource_type": row.resource_type,
        "resource_id": row.resource_id,
        "action": row.action,
        "effect": row.effect,
        "granted_by": str(row.granted_by) if row.granted_by else None,
        "expires_at": row.expires_at.isoformat() if row.expires_at else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


@router.get("/acls")
@inject
async def list_acls(
    resource_type: str | None = None,
    resource_id: str | None = None,
    subject_id: UUID | None = None,
    limit: int = 100,
    offset: int = 0,
    _: CurrentUser = Depends(require_permission(PermissionCode.ACL_READ)),
    uow_factory: Any = Depends(Provide[Container.unit_of_work]),
    acls: AclService = Depends(Provide[Container.acl_service]),
) -> list[dict[str, Any]]:
    async with uow_factory as uow:
        rows = await acls.list_entries(
            resource_type=resource_type,
            resource_id=resource_id,
            subject_id=subject_id,
            limit=limit,
            offset=offset,
        )
        await uow.commit()
        return [_acl_to_dict(row) for row in rows]


@router.post("/acls", status_code=201)
@inject
async def grant_acl(
    body: AclGrant,
    actor: CurrentUser = Depends(require_permission(PermissionCode.ACL_GRANT)),
    uow_factory: Any = Depends(Provide[Container.unit_of_work]),
    acls: AclService = Depends(Provide[Container.acl_service]),
) -> dict[str, Any]:
    async with uow_factory as uow:
        row = await acls.grant(
            subject_type=body.subject_type,
            subject_id=body.subject_id,
            resource_type=body.resource_type,
            resource_id=body.resource_id,
            action=body.action,
            effect=body.effect,
            granted_by=actor.id,
            expires_at=body.expires_at,
        )
        payload = _acl_to_dict(row)
        await uow.commit()
        return payload


@router.delete("/acls/{acl_id}", status_code=204)
@inject
async def revoke_acl(
    acl_id: UUID,
    _: CurrentUser = Depends(require_permission(PermissionCode.ACL_REVOKE)),
    uow_factory: Any = Depends(Provide[Container.unit_of_work]),
    acls: AclService = Depends(Provide[Container.acl_service]),
) -> None:
    async with uow_factory as uow:
        await acls.revoke(acl_id)
        await uow.commit()
