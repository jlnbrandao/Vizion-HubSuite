"""Namespaced permission codes stay interchangeable with their legacy aliases."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from src.shared.infrastructure.security.authorization import AuthorizationService
from src.shared.infrastructure.security.current_user import CurrentUser
from src.shared.infrastructure.security.permission_codes import (
    SERVICE_BY_RESOURCE,
    PermissionCode,
    service_for_resource,
)

TENANT = UUID("a0000000-0000-4000-8000-00000000000a")


def _user(*permissions: str) -> CurrentUser:
    return CurrentUser(
        id=uuid4(),
        email="u@x.com",
        full_name="User",
        tenant_id=TENANT,
        tenant_slug="universe",
        role_names=frozenset({"ADMIN"}),
        permissions=frozenset(permissions),
    )


def test_catalog_exposes_both_forms() -> None:
    definition = PermissionCode.definition_for("users.create")
    assert definition is not None
    assert definition.code == "iam.users.create"
    assert definition.legacy_code == "users.create"
    assert PermissionCode.definition_for("iam.users.create") is definition


def test_canonical_and_legacy_round_trip() -> None:
    assert PermissionCode.canonical("users.create") == "iam.users.create"
    assert PermissionCode.canonical("iam.users.create") == "iam.users.create"
    assert PermissionCode.legacy("iam.users.create") == "users.create"
    # Codes outside the catalog are left untouched.
    assert PermissionCode.canonical("gps.vehicles.read") == "gps.vehicles.read"
    assert PermissionCode.legacy("gps.vehicles.read") is None


def test_expand_adds_the_missing_alias() -> None:
    expanded = PermissionCode.expand(frozenset({"users.create"}))
    assert expanded == {"users.create", "iam.users.create"}

    expanded = PermissionCode.expand(frozenset({"iam.users.create"}))
    assert expanded == {"users.create", "iam.users.create"}


def test_every_resource_maps_to_a_service() -> None:
    for item in PermissionCode.catalog():
        assert item.service == service_for_resource(item.resource)
        assert SERVICE_BY_RESOURCE[item.resource] == item.service


def test_service_of_handles_unknown_and_namespaced_codes() -> None:
    assert PermissionCode.service_of("users.create") == "iam"
    assert PermissionCode.service_of("gps.vehicles.read") == "gps"
    assert PermissionCode.service_of("nonsense") is None


def test_platform_only_codes_cover_both_forms() -> None:
    platform_only = PermissionCode.platform_only_codes()
    assert "tenants.read" in platform_only
    assert "platform.tenants.read" in platform_only
    # ADMIN never holds product or platform codes.
    assert not (PermissionCode.admin_role_codes() & platform_only)


def test_bundles_reference_catalog_codes_only() -> None:
    for bundle in PermissionCode.bundles():
        assert bundle.codes, f"empty bundle: {bundle.slug}"
        assert bundle.slug.startswith(f"{bundle.service}.")
        assert set(bundle.codes) <= PermissionCode.known_codes()


def test_platform_bundle_has_no_product_codes() -> None:
    platform = PermissionCode.bundle("platform.admin")
    integration = PermissionCode.bundle("integration.admin")
    assert set(platform.codes) <= PermissionCode.platform_only_codes()
    assert set(integration.codes) <= PermissionCode.platform_only_codes()
    assert not (set(platform.codes) & set(integration.codes))


@pytest.mark.asyncio
@pytest.mark.parametrize("granted", ["users.create", "iam.users.create"])
@pytest.mark.parametrize("required", ["users.create", "iam.users.create"])
async def test_either_form_authorizes(granted: str, required: str) -> None:
    service = AuthorizationService()
    decision = await service.check(user=_user(granted), action=required)
    assert decision.allowed


@pytest.mark.asyncio
async def test_unrelated_code_still_denied() -> None:
    service = AuthorizationService()
    decision = await service.check(user=_user("iam.users.create"), action="iam.users.delete")
    assert not decision.allowed
