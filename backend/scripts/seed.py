"""Idempotent database seed: permissions, roles ADMIN…VIEWER, demo admin user.

Usage (from backend/):
    python -m scripts.seed
"""

from __future__ import annotations

import asyncio
import logging
import sys
from uuid import UUID

from src.modules.permissions.commands.permission_commands import CreatePermissionCommand
from src.modules.permissions.value_objects.permission_code import (
    PermissionCode as PermissionCodeVO,
)
from src.modules.roles.commands.role_commands import (
    CreateRoleCommand,
    ReplaceRolePermissionsCommand,
)
from src.modules.roles.value_objects.role_name import RoleName
from src.modules.users.commands.user_commands import (
    CreateUserCommand,
    ReplaceUserRolesCommand,
)
from src.modules.users.value_objects.email import Email
from src.shared.infrastructure.di.container import Container, create_container
from src.shared.infrastructure.di.register_handlers import register_module_handlers
from src.shared.infrastructure.security.permission_codes import PermissionCode

logger = logging.getLogger("seed")

DEMO_EMAIL = "galileu@lanstar.com.br"
DEMO_PASSWORD = "Demo@12345"
DEMO_FULL_NAME = "Galileu Admin"
DEMO_ROLE = "ADMIN"

ROLE_DESCRIPTIONS: dict[str, str] = {
    "ADMIN": "CRUD de usuários, roles e permissões",
    "MANAGER": "Company indicators and user oversight",
    "OPERATOR": "Day-to-day operations",
    "CLIENT": "Own profile access only",
    "VIEWER": "Read-only system overview",
}

# ADMIN: only identity/RBAC administration — no manager/operator/client/viewer/settings.
ADMIN_PERMISSIONS: frozenset[str] = frozenset(
    {
        PermissionCode.USERS_CREATE,
        PermissionCode.USERS_READ,
        PermissionCode.USERS_UPDATE,
        PermissionCode.USERS_DELETE,
        PermissionCode.USERS_ASSIGN_ROLES,
        PermissionCode.ROLES_CREATE,
        PermissionCode.ROLES_READ,
        PermissionCode.ROLES_UPDATE,
        PermissionCode.ROLES_DELETE,
        PermissionCode.ROLES_ASSIGN_PERMISSIONS,
        PermissionCode.PERMISSIONS_CREATE,
        PermissionCode.PERMISSIONS_READ,
        PermissionCode.PERMISSIONS_UPDATE,
        PermissionCode.PERMISSIONS_DELETE,
        PermissionCode.DASHBOARD_ADMIN,
    }
)

FORBIDDEN_FOR_ADMIN: frozenset[str] = frozenset(
    {
        PermissionCode.DASHBOARD_MANAGER,
        PermissionCode.DASHBOARD_OPERATOR,
        PermissionCode.DASHBOARD_CLIENT,
        PermissionCode.DASHBOARD_VIEWER,
        PermissionCode.SYSTEM_SETTINGS,
    }
)

ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "ADMIN": ADMIN_PERMISSIONS,
    "MANAGER": frozenset(
        {
            PermissionCode.USERS_READ,
            PermissionCode.USERS_UPDATE,
            PermissionCode.ROLES_READ,
            PermissionCode.PERMISSIONS_READ,
            PermissionCode.DASHBOARD_MANAGER,
        }
    ),
    "OPERATOR": frozenset(
        {
            PermissionCode.USERS_READ,
            PermissionCode.DASHBOARD_OPERATOR,
        }
    ),
    "CLIENT": frozenset(
        {
            PermissionCode.DASHBOARD_CLIENT,
        }
    ),
    "VIEWER": frozenset(
        {
            PermissionCode.USERS_READ,
            PermissionCode.ROLES_READ,
            PermissionCode.PERMISSIONS_READ,
            PermissionCode.DASHBOARD_VIEWER,
        }
    ),
}


def _permission_label(code: str) -> str:
    resource, action = code.split(".", 1)
    return f"{resource.replace('_', ' ').title()} {action.replace('_', ' ').title()}"


def validate_role_permissions_map() -> None:
    """Ensure ROLE_PERMISSIONS references canonical codes; ADMIN is RBAC-only."""
    all_codes = set(PermissionCode.all_codes())
    for role, codes in ROLE_PERMISSIONS.items():
        unknown = codes - all_codes
        if unknown:
            raise ValueError(f"Role {role} has unknown permission codes: {sorted(unknown)}")

    admin_codes = ROLE_PERMISSIONS["ADMIN"]
    missing = ADMIN_PERMISSIONS - admin_codes
    if missing:
        raise ValueError(f"ADMIN is missing required permission codes: {sorted(missing)}")

    forbidden = admin_codes & FORBIDDEN_FOR_ADMIN
    if forbidden:
        raise ValueError(
            f"ADMIN must not have non-RBAC permission codes: {sorted(forbidden)}"
        )


async def _ensure_permissions(container: Container) -> dict[str, UUID]:
    command_bus = container.command_bus()
    permissions = container.permission_repository()
    code_to_id: dict[str, UUID] = {}

    for code in PermissionCode.all_codes():
        async with container.unit_of_work():
            existing = await permissions.get_by_code(PermissionCodeVO.from_primitive(code))
        if existing is not None:
            code_to_id[code] = existing.id
            logger.info("permission exists: %s", code)
            continue

        permission_id = await command_bus.execute(
            CreatePermissionCommand(
                code=code,
                name=_permission_label(code),
                description=f"Permission {code}",
            )
        )
        code_to_id[code] = permission_id
        logger.info("permission created: %s", code)

    return code_to_id


async def _ensure_roles(
    container: Container, code_to_id: dict[str, UUID]
) -> dict[str, UUID]:
    command_bus = container.command_bus()
    roles = container.role_repository()
    role_to_id: dict[str, UUID] = {}

    for role_name, permission_codes in ROLE_PERMISSIONS.items():
        async with container.unit_of_work():
            existing = await roles.get_by_name(RoleName.from_primitive(role_name))
        if existing is not None:
            role_id = existing.id
            logger.info("role exists: %s", role_name)
        else:
            role_id = await command_bus.execute(
                CreateRoleCommand(
                    name=role_name,
                    description=ROLE_DESCRIPTIONS.get(role_name, ""),
                )
            )
            logger.info("role created: %s", role_name)

        permission_ids = frozenset(code_to_id[c] for c in permission_codes)
        await command_bus.execute(
            ReplaceRolePermissionsCommand(
                role_id=role_id,
                permission_ids=permission_ids,
            )
        )
        logger.info("role permissions set: %s (%d)", role_name, len(permission_ids))
        role_to_id[role_name] = role_id

    return role_to_id


async def _ensure_demo_user(container: Container, role_to_id: dict[str, UUID]) -> None:
    command_bus = container.command_bus()
    users = container.user_repository()
    admin_role_id = role_to_id[DEMO_ROLE]
    email = Email.from_primitive(DEMO_EMAIL)

    async with container.unit_of_work():
        existing = await users.get_by_email(email)

    if existing is None:
        await command_bus.execute(
            CreateUserCommand(
                email=DEMO_EMAIL,
                full_name=DEMO_FULL_NAME,
                password=DEMO_PASSWORD,
                role_ids=frozenset({admin_role_id}),
            )
        )
        logger.info("demo user created: %s", DEMO_EMAIL)
        return

    await command_bus.execute(
        ReplaceUserRolesCommand(
            user_id=existing.id,
            role_ids=frozenset({admin_role_id}),
        )
    )
    logger.info("demo user exists (roles refreshed): %s", DEMO_EMAIL)


async def seed() -> None:
    validate_role_permissions_map()
    container = create_container()
    register_module_handlers(container)

    try:
        code_to_id = await _ensure_permissions(container)
        role_to_id = await _ensure_roles(container, code_to_id)
        await _ensure_demo_user(container, role_to_id)
        logger.info("seed completed successfully")
    finally:
        engine = container.engine()
        await engine.dispose()
        redis = container.redis()
        await redis.aclose()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        stream=sys.stdout,
    )
    try:
        asyncio.run(seed())
    except Exception:
        logger.exception("seed failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
