"""Domain event subscribers — audit trail (stdout + durable DB when session available)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from src.modules.authentication.events.auth_events import (
    TokenRefreshedEvent,
    UserLoggedInEvent,
    UserLoggedOutEvent,
)
from src.modules.iam.models import AuditEventModel
from src.modules.permissions.events.permission_events import (
    PermissionCreatedEvent,
    PermissionDeletedEvent,
    PermissionUpdatedEvent,
)
from src.modules.roles.events.role_events import (
    PermissionsAssignedToRoleEvent,
    PermissionsRevokedFromRoleEvent,
    RoleCreatedEvent,
    RoleDeletedEvent,
    RoleUpdatedEvent,
)
from src.modules.users.events.user_events import (
    RolesAssignedToUserEvent,
    RolesRevokedFromUserEvent,
    UserCreatedEvent,
    UserDeletedEvent,
    UserPasswordChangedEvent,
    UserUpdatedEvent,
)
from src.shared.application.event_bus import EventBus
from src.shared.domain.domain_event import DomainEvent
from src.shared.infrastructure.session_context import get_current_session
from src.shared.infrastructure.tenant_context import get_current_tenant_id

if TYPE_CHECKING:
    from src.shared.infrastructure.di.container import Container

logger = logging.getLogger("vizion.audit")

_container: Container | None = None


async def _audit(event: DomainEvent) -> None:
    payload = event.to_dict()
    logger.info("AUDIT %s | %s", event.event_name, payload)
    tenant_id = get_current_tenant_id()
    if tenant_id is None:
        return
    try:
        session = get_current_session()
    except RuntimeError:
        if _container is None:
            return
        async with _container.unit_of_work() as uow:
            session = get_current_session()
            session.add(
                AuditEventModel(
                    id=uuid4(),
                    tenant_id=tenant_id,
                    actor_user_id=_actor_id(payload),
                    actor_type="human" if _actor_id(payload) else "system",
                    action=event.event_name,
                    resource_type=None,
                    resource_id=str(event.aggregate_id) if event.aggregate_id else None,
                    payload=payload,
                )
            )
            await uow.commit()
        return

    session.add(
        AuditEventModel(
            id=uuid4(),
            tenant_id=tenant_id,
            actor_user_id=_actor_id(payload),
            actor_type="human" if _actor_id(payload) else "system",
            action=event.event_name,
            resource_type=None,
            resource_id=str(event.aggregate_id) if event.aggregate_id else None,
            payload=payload,
        )
    )


def _actor_id(payload: dict[str, Any]) -> Any:
    for key in ("user_id", "actor_id"):
        raw = payload.get(key)
        if raw:
            from uuid import UUID

            try:
                return UUID(str(raw))
            except ValueError:
                return None
    return None


def register_audit_handlers(event_bus: EventBus, container: Container | None = None) -> None:
    global _container
    _container = container
    for event_type in (
        PermissionCreatedEvent,
        PermissionUpdatedEvent,
        PermissionDeletedEvent,
        RoleCreatedEvent,
        RoleUpdatedEvent,
        RoleDeletedEvent,
        PermissionsAssignedToRoleEvent,
        PermissionsRevokedFromRoleEvent,
        UserCreatedEvent,
        UserUpdatedEvent,
        UserDeletedEvent,
        UserPasswordChangedEvent,
        RolesAssignedToUserEvent,
        RolesRevokedFromUserEvent,
        UserLoggedInEvent,
        UserLoggedOutEvent,
        TokenRefreshedEvent,
    ):
        event_bus.subscribe(event_type, _audit)
