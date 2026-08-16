"""Versioned contracts between Platform Core and products."""

from openvizion.contracts.events import EventEnvelope
from openvizion.contracts.hub import (
    AuthorizeRequest,
    AuthorizeResponse,
    EntitlementCheckRequest,
    EntitlementCheckResponse,
    HeartbeatRequest,
    HubAuditRequest,
    HubEventRequest,
    HubTokenRequest,
    HubTokenResponse,
    IntrospectRequest,
    PrincipalResponse,
    TenantResponse,
)
from openvizion.contracts.products import (
    PRODUCT_SLUGS,
    ProductBinding,
    ProductInstance,
    ProductSlug,
)

__all__ = [
    "AuthorizeRequest",
    "AuthorizeResponse",
    "EntitlementCheckRequest",
    "EntitlementCheckResponse",
    "EventEnvelope",
    "HeartbeatRequest",
    "HubAuditRequest",
    "HubEventRequest",
    "HubTokenRequest",
    "HubTokenResponse",
    "IntrospectRequest",
    "PRODUCT_SLUGS",
    "PrincipalResponse",
    "ProductBinding",
    "ProductInstance",
    "ProductSlug",
    "TenantResponse",
]
