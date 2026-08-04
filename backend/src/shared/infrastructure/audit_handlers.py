"""Domain event subscribers — audit trail (stdout for now; swap for DB later)."""

from __future__ import annotations

import logging

from src.modules.authentication.events.auth_events import (
    TokenRefreshedEvent,
    UserLoggedInEvent,
    UserLoggedOutEvent,
)
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

logger = logging.getLogger("lanstar.audit")


async def _audit(event: DomainEvent) -> None:
    logger.info("AUDIT %s | %s", event.event_name, event.to_dict())


def register_audit_handlers(event_bus: EventBus) -> None:
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
