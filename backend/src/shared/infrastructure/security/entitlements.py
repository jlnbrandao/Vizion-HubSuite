"""Which services a principal can reach.

Two independent conditions, both required:

1. the tenant has the service contracted — `tenant_services` (Phase 6 catalog);
2. the principal holds at least one permission of that service.

The frontend uses the result to hide whole slices (menu + routes). The backend
still checks every individual permission, so this is presentation-level only.
"""

from __future__ import annotations

from collections.abc import Iterable

from src.shared.infrastructure.security.permission_codes import PermissionCode


def services_of(permissions: Iterable[str]) -> frozenset[str]:
    """Services referenced by a set of permission codes."""
    services = set()
    for code in permissions:
        service = PermissionCode.service_of(code)
        if service:
            services.add(service)
    return frozenset(services)


def entitled_services(
    permissions: Iterable[str],
    contracted: Iterable[str] | None = None,
) -> frozenset[str]:
    """Reachable services. `contracted=None` means the catalog is unavailable."""
    from_permissions = services_of(permissions)
    if contracted is None:
        return from_permissions
    return from_permissions & frozenset(contracted)
