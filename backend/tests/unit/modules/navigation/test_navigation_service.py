"""Navigation is filtered server-side: entitlement first, then RBAC."""

from __future__ import annotations

from uuid import uuid4

from src.modules.navigation.service import NavigationService
from src.shared.infrastructure.security.current_user import CurrentUser
from src.shared.infrastructure.security.permission_codes import PermissionCode


def _user(*permissions: str) -> CurrentUser:
    return CurrentUser(
        id=uuid4(),
        email="user@vizion.io",
        full_name="User",
        tenant_id=uuid4(),
        tenant_slug="acme",
        permissions=frozenset(permissions),
    )


def _ids(user: CurrentUser) -> set[str]:
    return {item.id for item in NavigationService().resolve(user).items}


def test_admin_sees_rbac_entries_but_not_platform() -> None:
    ids = _ids(
        _user(
            PermissionCode.DASHBOARD_ADMIN,
            PermissionCode.USERS_READ,
            PermissionCode.ROLES_READ,
            PermissionCode.PERMISSIONS_READ,
            PermissionCode.ACL_READ,
        )
    )

    assert {"admin-users", "admin-roles", "admin-permissions", "iam-acls"} <= ids
    assert "platform-tenants" not in ids
    assert "integration-hub" not in ids


def test_entries_are_hidden_when_the_service_is_not_entitled() -> None:
    """Holding the code is not enough: the owning service must be reachable."""
    service = NavigationService()
    entitled = service.resolve(_user(PermissionCode.INTEGRATION_READ))
    assert "integration" in entitled.services
    assert "integration-hub" in {item.id for item in entitled.items}

    # dashboard.* belongs to iam, so the integration slice stays hidden.
    other = service.resolve(_user(PermissionCode.DASHBOARD_VIEWER))
    assert "integration" not in other.services
    assert "integration-hub" not in {item.id for item in other.items}


def test_uncontracted_service_disappears_even_with_permissions() -> None:
    user = _user(PermissionCode.INTEGRATION_READ, PermissionCode.USERS_READ)

    view = NavigationService().resolve(user, frozenset({"iam"}))

    ids = {item.id for item in view.items}
    assert "admin-users" in ids
    assert "integration-hub" not in ids
    assert view.services == ("iam",)


def test_canonical_codes_are_accepted() -> None:
    assert "admin-users" in _ids(_user("iam.users.read"))


def test_client_only_user_lands_on_the_map() -> None:
    view = NavigationService().resolve(_user(PermissionCode.DASHBOARD_CLIENT))

    assert view.home_route == "/main"
    home = next(item for item in view.items if item.id == "nav-home")
    assert home.route == "/main"
    # No duplicate map entry next to home.
    assert [item.id for item in view.items].count("client-map") == 0
    assert "client-profile" in {item.id for item in view.items}


def test_usage_entry_accepts_either_own_or_cross_tenant_code() -> None:
    assert "platform-usage" in _ids(_user(PermissionCode.USAGE_READ))
    assert "platform-usage" in _ids(_user(PermissionCode.USAGE_READ_ALL))
    assert "platform-usage" not in _ids(_user(PermissionCode.TENANTS_READ))


def test_self_service_entries_need_no_permission() -> None:
    ids = _ids(_user())

    assert {"nav-home", "account-profile", "account-sessions", "account-mfa"} <= ids
    assert "admin-users" not in ids
    assert "account-billing" not in ids


def test_billing_appears_only_when_entitled_and_permitted() -> None:
    with_perm = NavigationService().resolve(
        _user(PermissionCode.INVOICES_READ), frozenset({"iam", "billing"})
    )
    assert "account-billing" in {item.id for item in with_perm.items}

    platform_only = NavigationService().resolve(
        _user(PermissionCode.DASHBOARD_PLATFORM), frozenset({"iam", "platform"})
    )
    assert "account-billing" not in {item.id for item in platform_only.items}
