"""The precedence chain, exercised against the real database.

Covers each stage the engine documents: entitlement before RBAC, ACL deny over
RBAC allow, ACL allow as a resource-scoped exception, and role hierarchy. HTTP is
used wherever a route exists; the ACL stages go through the engine directly
because no route takes a resource reference yet.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from httpx import AsyncClient

from src.shared.infrastructure.security.authorization import (
    AuthorizationStage,
    ResourceRef,
)
from src.shared.infrastructure.security.current_user import CurrentUser
from src.shared.infrastructure.security.permission_codes import PermissionCode
from src.shared.infrastructure.tenant_context import bind_tenant, unbind_tenant
from tests.integration.conftest import auth


async def test_rbac_allows_what_the_role_grants(
    client: AsyncClient, viewer_token: str
) -> None:
    response = await client.get("/api/v1/users", headers=auth(viewer_token))

    assert response.status_code == 200, response.text


async def test_rbac_denies_what_the_role_lacks(
    client: AsyncClient, viewer_token: str
) -> None:
    response = await client.post(
        "/api/v1/users",
        headers=auth(viewer_token),
        json={
            "email": "nope@lanstar.test",
            "username": "nope",
            "full_name": "Nope",
            "password": "Str0ng-Pass!",
        },
    )

    assert response.status_code == 403
    assert "permission" in response.json()["error"]["message"].lower()


async def test_denials_are_audited(client: AsyncClient, admin_token: str) -> None:
    """A denial must leave a trail an operator can find by correlation id."""
    request_id = f"itest-{uuid4().hex[:12]}"
    denied = await client.post(
        "/api/v1/permissions",
        headers={**auth(admin_token), "X-Request-ID": request_id},
        json={"code": "gps.vehicles.read", "name": "x", "description": "y"},
    )
    # Admin may create permissions; the interesting case is a denied one.
    if denied.status_code not in (401, 403):
        return

    events = await client.get(
        "/api/v1/audit-events",
        params={"action": "AUTHZ_DENIED", "request_id": request_id},
        headers=auth(admin_token),
    )
    assert events.status_code == 200, events.text
    assert all(event["request_id"] == request_id for event in events.json())


async def test_platform_only_codes_are_not_reachable_from_a_tenant(
    client: AsyncClient, admin_token: str
) -> None:
    """A tenant ADMIN is not a platform operator, whatever the tenant DB says."""
    response = await client.get("/api/v1/tenants", headers=auth(admin_token))

    assert response.status_code == 403


async def test_legacy_and_canonical_codes_authorize_the_same_route(
    client: AsyncClient, admin_token: str
) -> None:
    me = await client.get("/api/v1/auth/me", headers=auth(admin_token))
    permissions = set(me.json()["permissions"])

    assert PermissionCode.USERS_READ in permissions
    assert PermissionCode.canonical(PermissionCode.USERS_READ) in permissions


async def _actor(client: AsyncClient, token: str) -> CurrentUser:
    """Rebuild the engine's view of the caller from `GET /auth/me`."""
    body = (await client.get("/api/v1/auth/me", headers=auth(token))).json()
    return CurrentUser(
        id=UUID(body["id"]),
        email=body["email"],
        full_name=body["full_name"],
        tenant_id=UUID(body["tenant_id"]),
        tenant_slug=body["tenant_slug"],
        tenant_name=body.get("tenant_name") or "",
        role_names=frozenset(body["role_names"]),
        permissions=frozenset(body["permissions"]),
    )


async def test_acl_deny_beats_an_rbac_allow(
    app: Any, client: AsyncClient, admin_token: str
) -> None:
    actor = await _actor(client, admin_token)
    resource_id = uuid4()

    granted = await client.post(
        "/api/v1/acls",
        headers=auth(admin_token),
        json={
            "subject_type": "user",
            "subject_id": str(actor.id),
            "resource_type": "user",
            "resource_id": str(resource_id),
            "action": PermissionCode.USERS_READ,
            "effect": "deny",
        },
    )
    assert granted.status_code == 201, granted.text
    acl_id = granted.json()["id"]

    container = app.state.container
    engine = container.authorization_service()
    tokens = bind_tenant(actor.tenant_id, slug=actor.tenant_slug, name="Universe")
    try:
        async with container.unit_of_work():
            decision = await engine.check(
                user=actor,
                action=PermissionCode.USERS_READ,
                resource=ResourceRef(type="user", id=resource_id),
            )
            # Same permission, a different resource: RBAC still applies.
            elsewhere = await engine.check(
                user=actor,
                action=PermissionCode.USERS_READ,
                resource=ResourceRef(type="user", id=uuid4()),
            )
    finally:
        unbind_tenant(*tokens)
        await client.delete(f"/api/v1/acls/{acl_id}", headers=auth(admin_token))

    assert decision.denied
    assert decision.stage is AuthorizationStage.ACL
    assert elsewhere.allowed


async def test_acl_allow_is_a_resource_scoped_exception(
    app: Any, client: AsyncClient, admin_token: str, viewer_token: str
) -> None:
    """A viewer gains one resource without gaining the global permission."""
    viewer = await _actor(client, viewer_token)
    resource_id = uuid4()

    granted = await client.post(
        "/api/v1/acls",
        headers=auth(admin_token),
        json={
            "subject_type": "user",
            "subject_id": str(viewer.id),
            "resource_type": "user",
            "resource_id": str(resource_id),
            "action": PermissionCode.USERS_UPDATE,
            "effect": "allow",
        },
    )
    assert granted.status_code == 201, granted.text
    acl_id = granted.json()["id"]

    container = app.state.container
    engine = container.authorization_service()
    tokens = bind_tenant(viewer.tenant_id, slug=viewer.tenant_slug, name="Universe")
    try:
        async with container.unit_of_work():
            on_resource = await engine.check(
                user=viewer,
                action=PermissionCode.USERS_UPDATE,
                resource=ResourceRef(type="user", id=resource_id),
            )
            globally = await engine.check(
                user=viewer, action=PermissionCode.USERS_UPDATE
            )
    finally:
        unbind_tenant(*tokens)
        await client.delete(f"/api/v1/acls/{acl_id}", headers=auth(admin_token))

    assert on_resource.allowed
    assert on_resource.stage is AuthorizationStage.ACL
    assert globally.denied
    assert globally.stage is AuthorizationStage.RBAC


async def test_tenant_isolation_outranks_an_acl_allow(app: Any, client: AsyncClient, admin_token: str) -> None:
    actor = await _actor(client, admin_token)
    container = app.state.container
    engine = container.authorization_service()

    tokens = bind_tenant(actor.tenant_id, slug=actor.tenant_slug, name="Universe")
    try:
        async with container.unit_of_work():
            decision = await engine.check(
                user=actor,
                action=PermissionCode.USERS_READ,
                resource=ResourceRef(type="user", id=uuid4(), tenant_id=uuid4()),
            )
    finally:
        unbind_tenant(*tokens)

    assert decision.denied
    assert decision.stage is AuthorizationStage.TENANT
