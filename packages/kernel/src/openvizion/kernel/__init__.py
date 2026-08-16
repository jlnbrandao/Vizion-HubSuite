"""Product kernel ports — no FastAPI, SQLAlchemy, Redis, Kafka or Platform Core."""

from openvizion.kernel.audit import AuditRecord, AuditProvider
from openvizion.kernel.authorization import AuthorizationDecision, AuthorizationProvider
from openvizion.kernel.configuration import AdapterSelection, DeploymentMode, KernelSettings
from openvizion.kernel.entitlements import EntitlementProvider
from openvizion.kernel.identity import Principal, TenantInfo
from openvizion.kernel.platform import PlatformAdapter
from openvizion.kernel.tenant import TenantContext, TenantResolver

__all__ = [
    "AdapterSelection",
    "AuditProvider",
    "AuditRecord",
    "AuthorizationDecision",
    "AuthorizationProvider",
    "DeploymentMode",
    "EntitlementProvider",
    "KernelSettings",
    "PlatformAdapter",
    "Principal",
    "TenantContext",
    "TenantInfo",
    "TenantResolver",
]
