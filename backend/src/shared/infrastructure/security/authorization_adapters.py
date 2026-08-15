"""Adapters that plug concrete IAM services into the AuthorizationService ports."""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from contextlib import AbstractAsyncContextManager
from time import monotonic
from typing import Any
from uuid import UUID

from src.config.settings import Settings
from src.modules.iam.abac.service import AbacService
from src.modules.iam.acl.service import AclService
from src.modules.iam.audit.service import AuditService
from src.modules.services.service import ServiceCatalogService
from src.shared.application.unit_of_work import UnitOfWork
from src.shared.infrastructure.security.authorization import (
    AbacGate,
    AclEffect,
    AclProvider,
    AuthorizationAuditSink,
    Decision,
    EntitlementProvider,
    RequestContext,
    ResourceRef,
)
from src.shared.infrastructure.security.current_user import CurrentUser
from src.shared.infrastructure.session_context import get_current_session

logger = logging.getLogger("lanstar.authz")

UowFactory = Callable[[], AbstractAsyncContextManager[UnitOfWork]]

AUTHZ_DENIED_ACTION = "AUTHZ_DENIED"


class AbacServiceGate(AbacGate):
    """Evaluates `access_policies` when ABAC is on and a DB session is bound.

    Without a session there is nothing to read policies from, so the gate abstains
    (returns True) and the decision is left to the stages around it.
    """

    def __init__(self, abac_service: AbacService, settings: Settings) -> None:
        self._abac = abac_service
        self._settings = settings

    async def allows(
        self,
        *,
        subject_attributes: Mapping[str, Any],
        action: str,
        resource_attributes: Mapping[str, Any],
        environment: Mapping[str, Any],
    ) -> bool:
        if not self._settings.iam_abac_enabled:
            return True
        try:
            get_current_session()
        except RuntimeError:
            return True

        policies = await self._abac.list_policies()
        return self._abac.enforcer.enforce(
            policies=policies,
            subject_attrs=dict(subject_attributes),
            action=action,
            resource_attrs=dict(resource_attributes),
            env=dict(environment),
        )


class AclServiceProvider(AclProvider):
    """Reads `resource_acls`. Abstains when no DB session is bound to the request."""

    def __init__(self, acl_service: AclService) -> None:
        self._acls = acl_service

    async def effect_for(
        self,
        *,
        user: CurrentUser,
        action: str,
        resource: ResourceRef,
    ) -> AclEffect | None:
        if resource.id is None:
            return None
        try:
            get_current_session()
        except RuntimeError:
            return None

        effects = await self._acls.effects_for(
            user_id=user.id,
            role_ids=user.role_ids,
            resource_type=resource.type,
            resource_id=str(resource.id),
            action=action,
        )
        if not effects:
            return None
        # A single deny outranks every allow on the same resource.
        if AclEffect.DENY in effects:
            return AclEffect.DENY
        return AclEffect.ALLOW


class CatalogEntitlementProvider(EntitlementProvider):
    """Reads `tenant_services`, with a short-lived per-tenant cache.

    The stage runs on every permission check, so the answer is cached for a few
    seconds; platform administration calls `invalidate()` when it changes a
    contract. When the catalog cannot be read at all the provider abstains
    (allows) and leaves the decision to RBAC — an infrastructure hiccup must not
    lock every tenant out of the Hub.
    """

    def __init__(
        self,
        catalog: ServiceCatalogService,
        uow_factory: UowFactory,
        ttl_seconds: int = 30,
    ) -> None:
        self._catalog = catalog
        self._uow_factory = uow_factory
        self._ttl = ttl_seconds
        self._cache: dict[UUID, tuple[float, frozenset[str]]] = {}

    async def is_entitled(self, *, tenant_id: UUID, service: str) -> bool:
        namespaces = await self._namespaces(tenant_id)
        return namespaces is None or service in namespaces

    def invalidate(self, tenant_id: UUID | None = None) -> None:
        if tenant_id is None:
            self._cache.clear()
        else:
            self._cache.pop(tenant_id, None)

    async def _namespaces(self, tenant_id: UUID) -> frozenset[str] | None:
        """None means "unknown" — callers treat it as abstain."""
        now = monotonic()
        cached = self._cache.get(tenant_id)
        if cached is not None and cached[0] > now:
            return cached[1]

        try:
            namespaces = await self._read(tenant_id)
        except Exception:  # noqa: BLE001 - never fail closed on catalog errors
            logger.warning("Could not read tenant entitlements", exc_info=True)
            return None

        self._cache[tenant_id] = (now + self._ttl, namespaces)
        return namespaces

    async def _read(self, tenant_id: UUID) -> frozenset[str]:
        try:
            get_current_session()
        except RuntimeError:
            # Authorization usually runs before the route opens its own session.
            async with self._uow_factory():
                return await self._catalog.entitled_namespaces(tenant_id)
        return await self._catalog.entitled_namespaces(tenant_id)


class AuditingAuthorizationSink(AuthorizationAuditSink):
    """Records denials in the audit trail, never blocking the request on failure."""

    def __init__(self, audit_service: AuditService, uow_factory: UowFactory) -> None:
        self._audit = audit_service
        self._uow_factory = uow_factory

    async def record_denied(
        self,
        *,
        user: CurrentUser,
        action: str,
        resource: ResourceRef | None,
        decision: Decision,
        context: RequestContext | None,
    ) -> None:
        payload = {
            "action": action,
            "stage": str(decision.stage),
            "reason": decision.reason,
            "resource_type": resource.type if resource else None,
        }
        logger.info("AUTHZ_DENIED %s", payload)
        try:
            await self._persist(user=user, resource=resource, context=context, payload=payload)
        except Exception:  # noqa: BLE001 - auditing must never break authorization
            logger.warning("Failed to persist AUTHZ_DENIED event", exc_info=True)

    async def _persist(
        self,
        *,
        user: CurrentUser,
        resource: ResourceRef | None,
        context: RequestContext | None,
        payload: dict[str, Any],
    ) -> None:
        resource_id = str(resource.id) if resource and resource.id else None
        ip = context.ip if context else None
        user_agent = context.user_agent if context else None

        try:
            get_current_session()
        except RuntimeError:
            async with self._uow_factory() as uow:
                await self._audit.persist(
                    action=AUTHZ_DENIED_ACTION,
                    actor_user_id=user.id,
                    actor_type="human",
                    resource_type=resource.type if resource else None,
                    resource_id=resource_id,
                    ip_address=ip,
                    user_agent=user_agent,
                    payload=payload,
                    tenant_id=user.tenant_id,
                )
                await uow.commit()
            return

        await self._audit.persist(
            action=AUTHZ_DENIED_ACTION,
            actor_user_id=user.id,
            actor_type="human",
            resource_type=resource.type if resource else None,
            resource_id=resource_id,
            ip_address=ip,
            user_agent=user_agent,
            payload=payload,
            tenant_id=user.tenant_id,
        )
