"""Declarative catalog of services shipped with the Hub.

Hub modules (IAM, platform, integration, billing) live in CORE_SERVICES and are
mounted in-process. Distributable products (Tracking, IoT, SNMP, GIS) live in
PRODUCT_SERVICES: they are sellable entitlements, not FastAPI routers of the Hub.
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

PRODUCT_SERVICES: tuple[ServiceDefinition, ...] = (
    ServiceDefinition(
        slug="tracking",
        namespace="tracking",
        name="Tracking",
        description="GPS tracking product — devices, positions, geofences",
        tenant_only=True,
        default_quotas={"devices": 100},
    ),
    ServiceDefinition(
        slug="iot",
        namespace="iot",
        name="IoT",
        description="IoT product scaffold",
        tenant_only=True,
    ),
    ServiceDefinition(
        slug="snmp",
        namespace="snmp",
        name="SNMP",
        description="SNMP product scaffold",
        tenant_only=True,
    ),
    ServiceDefinition(
        slug="gis",
        namespace="gis",
        name="GIS",
        description="GIS product — maps and geospatial workspace",
        tenant_only=True,
    ),
    ServiceDefinition(
        slug="lanstar",
        namespace="lanstar",
        name="Lanstar",
        description="Lanstar GPS — public UI proxied at lanstar.openvizion.com",
        tenant_only=True,
    ),
)

ALL_SERVICES: tuple[ServiceDefinition, ...] = CORE_SERVICES + PRODUCT_SERVICES

