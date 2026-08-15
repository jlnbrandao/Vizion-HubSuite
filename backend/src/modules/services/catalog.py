"""Declarative catalog of services shipped with the Hub.

A new service slice adds an entry here (and a row in `services` via the seed),
which is what makes its permission namespace sellable per tenant. Products that
are not part of this repository yet — GPS, SNMP, DDNS, ERP — are intentionally
absent: they plug in by adding their own entry.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.shared.infrastructure.security.permission_codes import (
    SERVICE_BILLING,
    SERVICE_IAM,
    SERVICE_INTEGRATION,
    SERVICE_PLATFORM,
)

#: Ops tenant (`ows`) never receives tenant-only services such as billing.
PLATFORM_TENANT_SLUG = "ows"


@dataclass(frozen=True, slots=True)
class ServiceDefinition:
    slug: str
    namespace: str
    name: str
    description: str
    version: str = "1.0"
    #: The Hub cannot run without it, so it can never be suspended or disabled.
    is_core: bool = False
    #: Enabled for every new tenant. Sellable services leave this off.
    enabled_by_default: bool = False
    #: Product-tenant service: never entitled on the platform tenant (`ows`).
    tenant_only: bool = False
    #: Baseline quotas; `tenant_services.quotas` overrides individual keys.
    default_quotas: dict[str, Any] = field(default_factory=dict)


CORE_SERVICES: tuple[ServiceDefinition, ...] = (
    ServiceDefinition(
        slug=SERVICE_IAM,
        namespace=SERVICE_IAM,
        name="Identity & Access",
        description="Users, roles, permissions, MFA, sessions and audit",
        is_core=True,
        enabled_by_default=True,
    ),
    ServiceDefinition(
        slug=SERVICE_PLATFORM,
        namespace=SERVICE_PLATFORM,
        name="Platform",
        description="Tenant catalog, entitlements and cross-tenant administration",
        is_core=True,
        enabled_by_default=True,
    ),
    ServiceDefinition(
        slug=SERVICE_INTEGRATION,
        namespace=SERVICE_INTEGRATION,
        name="Integration Hub",
        description="Outbound integrations, webhooks and synchronization",
        # Ships with the product and is on for new tenants, but it is a service
        # like any other: the platform may suspend it per tenant.
        enabled_by_default=True,
        default_quotas={"sync_per_hour": 60},
    ),
    ServiceDefinition(
        slug=SERVICE_BILLING,
        namespace=SERVICE_BILLING,
        name="Billing",
        description="Invoices and payments for contracted tenant services",
        tenant_only=True,
        enabled_by_default=True,
    ),
)

CORE_SERVICE_SLUGS: frozenset[str] = frozenset(item.slug for item in CORE_SERVICES)
DEFAULT_SERVICE_SLUGS: frozenset[str] = frozenset(
    item.slug for item in CORE_SERVICES if item.enabled_by_default
)
