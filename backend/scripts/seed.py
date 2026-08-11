"""Idempotent database seed: permissions, roles ADMIN…VIEWER, demo users.

Usage (from backend/):
    python -m scripts.seed
"""

from __future__ import annotations

import asyncio
import logging
import sys
from dataclasses import dataclass
from uuid import UUID

from src.modules.permissions.commands.permission_commands import (
    CreatePermissionCommand,
    DeletePermissionCommand,
    UpdatePermissionCommand,
)
from src.modules.permissions.value_objects.permission_code import (
    PermissionCode as PermissionCodeVO,
)
from src.modules.roles.commands.role_commands import (
    CreateRoleCommand,
    ReplaceRolePermissionsCommand,
)
from src.modules.roles.value_objects.role_name import RoleName
from src.modules.tenants.commands.tenant_commands import UpsertTenantCommand
from src.modules.users.commands.user_commands import (
    ChangeUserPasswordCommand,
    CreateUserCommand,
    ReplaceUserRolesCommand,
    UpdateUserCommand,
)
from src.modules.users.value_objects.email import Email
from src.modules.users.value_objects.username import Username
from src.shared.infrastructure.di.container import Container, create_container
from src.shared.infrastructure.di.register_handlers import register_module_handlers
from src.shared.infrastructure.security.permission_codes import PermissionCode
from src.shared.infrastructure.tenant_context import (
    bind_rls_bypass,
    bind_tenant,
    unbind_rls_bypass,
    unbind_tenant,
)

logger = logging.getLogger("seed")

BIGBANG_TENANT_ID = UUID("a0000000-0000-4000-8000-000000000001")
PLATFORM_TENANT_ID = UUID("a0000000-0000-4000-8000-000000000002")
SEED_PASSWORD = "123Mudar."


@dataclass(frozen=True, slots=True)
class SeedUser:
    username: str
    full_name: str
    email: str
    role: str


SEED_USERS: tuple[SeedUser, ...] = (
    SeedUser("admin", "System Administrator", "admin@lanstar.com.br", "ADMIN"),
    SeedUser("manager", "Default Manager", "manager@lanstar.com.br", "MANAGER"),
    SeedUser("operator", "Default Operator", "operator@lanstar.com.br", "OPERATOR"),
    SeedUser("user", "Default User", "user@lanstar.com.br", "CLIENT"),
    SeedUser("viewer", "Default Viewer", "viewer@lanstar.com.br", "VIEWER"),
)

# Former emails remapped on refresh (e.g. teste@ → user@).
LEGACY_EMAILS: dict[str, str] = {
    "teste@lanstar.com.br": "user@lanstar.com.br",
    "galileu@lanstar.com.br": "admin@lanstar.com.br",
    "platform@lanstar.com.br": "galileu@lanstar.com.br",
}

# Former usernames remapped on refresh (old → new).
LEGACY_USERNAMES: dict[str, str] = {
    "galileu": "admin",
    "platform": "galileu",
}

# Old compound action codes retired in favor of bare PermissionAction.ASSIGN.
OBSOLETE_PERMISSION_CODES: frozenset[str] = frozenset(
    {
        "users.assign_roles",
        "roles.assign_permissions",
        "navigation.create",
        "navigation.read",
        "navigation.update",
        "navigation.delete",
    }
)

ROLE_DESCRIPTIONS: dict[str, str] = {
    "ADMIN": "CRUD for users, roles, and permissions",
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
        PermissionCode.USERS_ASSIGN,
        PermissionCode.ROLES_CREATE,
        PermissionCode.ROLES_READ,
        PermissionCode.ROLES_UPDATE,
        PermissionCode.ROLES_DELETE,
        PermissionCode.ROLES_ASSIGN,
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
        *PermissionCode.platform_only_codes(),
    }
)

PLATFORM_PERMISSIONS: frozenset[str] = frozenset(PermissionCode.platform_only_codes())

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


def _permission_meta(code: str) -> tuple[str, str]:
    definition = PermissionCode.definition_for(code)
    if definition is not None:
        return definition.name, definition.description
    resource, action = code.split(".", 1)
    name = f"{resource.replace('_', ' ').title()} {action.replace('_', ' ').title()}"
    return name, f"Permission {code}"


def validate_role_permissions_map() -> None:
    """Ensure ROLE_PERMISSIONS references canonical codes; ADMIN is RBAC-only."""
    all_codes = set(PermissionCode.all_codes())
    catalog_codes = {item.code for item in PermissionCode.catalog()}
    missing_meta = all_codes - catalog_codes
    if missing_meta:
        raise ValueError(
            f"PERMISSION_CATALOG missing metadata for: {sorted(missing_meta)}"
        )

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


async def _ensure_permissions(
    container: Container,
    *,
    tenant_id: UUID,
    codes: tuple[str, ...] | frozenset[str] | None = None,
) -> dict[str, UUID]:
    command_bus = container.command_bus()
    permissions = container.permission_repository()
    code_to_id: dict[str, UUID] = {}
    selected = tuple(codes) if codes is not None else PermissionCode.all_codes()

    for code in selected:
        name, description = _permission_meta(code)
        async with container.unit_of_work():
            existing = await permissions.get_by_code(PermissionCodeVO.from_primitive(code))
        if existing is not None:
            code_to_id[code] = existing.id
            if existing.name.value != name or existing.description != description:
                await command_bus.execute(
                    UpdatePermissionCommand(
                        permission_id=existing.id,
                        name=name,
                        description=description,
                        is_active=existing.is_active,
                    )
                )
                logger.info("permission metadata synced: %s", code)
            else:
                logger.info("permission exists: %s", code)
            continue

        permission_id = await command_bus.execute(
            CreatePermissionCommand(
                tenant_id=tenant_id,
                code=code,
                name=name,
                description=description,
            )
        )
        code_to_id[code] = permission_id
        logger.info("permission created: %s", code)

    return code_to_id


async def _ensure_roles(
    container: Container,
    code_to_id: dict[str, UUID],
    *,
    tenant_id: UUID,
    role_permissions: dict[str, frozenset[str]],
    role_descriptions: dict[str, str] | None = None,
) -> dict[str, UUID]:
    command_bus = container.command_bus()
    roles = container.role_repository()
    role_to_id: dict[str, UUID] = {}
    descriptions = role_descriptions or ROLE_DESCRIPTIONS

    for role_name, permission_codes in role_permissions.items():
        async with container.unit_of_work():
            existing = await roles.get_by_name(RoleName.from_primitive(role_name))
        if existing is not None:
            role_id = existing.id
            logger.info("role exists: %s", role_name)
        else:
            role_id = await command_bus.execute(
                CreateRoleCommand(
                    tenant_id=tenant_id,
                    name=role_name,
                    description=descriptions.get(role_name, ""),
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


async def _retire_obsolete_permissions(container: Container) -> None:
    """Remove legacy compound codes after roles point at the new catalog."""
    command_bus = container.command_bus()
    permissions = container.permission_repository()

    for code in sorted(OBSOLETE_PERMISSION_CODES):
        async with container.unit_of_work():
            existing = await permissions.get_by_code(PermissionCodeVO.from_primitive(code))
        if existing is None:
            continue
        await command_bus.execute(DeletePermissionCommand(permission_id=existing.id))
        logger.info("obsolete permission removed: %s", code)


async def _find_existing_user(container: Container, seed_user: SeedUser):
    users = container.user_repository()
    email = Email.from_primitive(seed_user.email)
    username = Username.from_primitive(seed_user.username)
    legacy_emails = [
        Email.from_primitive(old)
        for old, new in LEGACY_EMAILS.items()
        if new == seed_user.email
    ]
    legacy_usernames = [
        Username.from_primitive(old)
        for old, new in LEGACY_USERNAMES.items()
        if new == seed_user.username
    ]

    async with container.unit_of_work():
        by_email = await users.get_by_email(email)
        if by_email is not None:
            return by_email
        for legacy in legacy_emails:
            by_legacy = await users.get_by_email(legacy)
            if by_legacy is not None:
                return by_legacy
        by_username = await users.get_by_username(username)
        if by_username is not None:
            return by_username
        for legacy_username in legacy_usernames:
            by_legacy_username = await users.get_by_username(legacy_username)
            if by_legacy_username is not None:
                return by_legacy_username
        return None


async def _ensure_seed_users(
    container: Container,
    role_to_id: dict[str, UUID],
    *,
    tenant_id: UUID,
    seed_users: tuple[SeedUser, ...] = SEED_USERS,
) -> None:
    command_bus = container.command_bus()
    users = container.user_repository()

    for seed_user in seed_users:
        role_id = role_to_id[seed_user.role]
        existing = await _find_existing_user(container, seed_user)

        if existing is None:
            await command_bus.execute(
                CreateUserCommand(
                    tenant_id=tenant_id,
                    email=seed_user.email,
                    username=seed_user.username,
                    full_name=seed_user.full_name,
                    password=SEED_PASSWORD,
                    role_ids=frozenset({role_id}),
                )
            )
            logger.info("seed user created: %s (%s)", seed_user.username, seed_user.role)
            continue

        target_email = Email.from_primitive(seed_user.email)
        if existing.email != target_email:
            async with container.unit_of_work() as uow:
                user = await users.get_by_id(existing.id)
                if user is None:
                    continue
                conflict = await users.get_by_email(target_email)
                if conflict is not None and conflict.id != user.id:
                    raise RuntimeError(
                        f"Cannot remap email to {seed_user.email}: already in use"
                    )
                user.change_email(target_email)
                await users.update(user)
                uow.track(user)
                await uow.commit()
            logger.info(
                "seed user email remapped: %s → %s",
                existing.email.value,
                seed_user.email,
            )

        await command_bus.execute(
            UpdateUserCommand(
                user_id=existing.id,
                username=seed_user.username,
                full_name=seed_user.full_name,
                is_active=True,
            )
        )
        await command_bus.execute(
            ChangeUserPasswordCommand(
                user_id=existing.id,
                new_password=SEED_PASSWORD,
            )
        )
        await command_bus.execute(
            ReplaceUserRolesCommand(
                user_id=existing.id,
                role_ids=frozenset({role_id}),
            )
        )
        logger.info(
            "seed user refreshed: %s (%s)",
            seed_user.username,
            seed_user.role,
        )


async def _seed_tenant(
    container: Container,
    *,
    tenant_id: UUID,
    slug: str,
    name: str,
    permission_codes: tuple[str, ...] | frozenset[str],
    role_permissions: dict[str, frozenset[str]],
    seed_users: tuple[SeedUser, ...],
    role_descriptions: dict[str, str] | None = None,
) -> None:
    id_token, slug_token, name_token = bind_tenant(tenant_id, slug=slug, name=name)
    try:
        await container.command_bus().execute(
            UpsertTenantCommand(slug=slug, name=name, tenant_id=tenant_id)
        )
        code_to_id = await _ensure_permissions(
            container, tenant_id=tenant_id, codes=permission_codes
        )
        role_to_id = await _ensure_roles(
            container,
            code_to_id,
            tenant_id=tenant_id,
            role_permissions=role_permissions,
            role_descriptions=role_descriptions,
        )
        if slug == "bigbang":
            await _retire_obsolete_permissions(container)
        await _ensure_seed_users(
            container, role_to_id, tenant_id=tenant_id, seed_users=seed_users
        )
    finally:
        unbind_tenant(id_token, slug_token, name_token)


async def seed() -> None:
    validate_role_permissions_map()
    container = create_container()
    register_module_handlers(container)

    tenant_scoped_codes = tuple(
        code
        for code in PermissionCode.all_codes()
        if code not in PermissionCode.platform_only_codes()
    )

    bypass_token = bind_rls_bypass(True)
    try:
        await _seed_tenant(
            container,
            tenant_id=BIGBANG_TENANT_ID,
            slug="bigbang",
            name="Bigbang",
            permission_codes=tenant_scoped_codes,
            role_permissions=ROLE_PERMISSIONS,
            seed_users=SEED_USERS,
        )
        await _seed_tenant(
            container,
            tenant_id=PLATFORM_TENANT_ID,
            slug="platform",
            name="Platform",
            permission_codes=PLATFORM_PERMISSIONS,
            role_permissions={"PLATFORM": PLATFORM_PERMISSIONS},
            seed_users=(
                SeedUser(
                    "galileu",
                    "Platform Operator",
                    "galileu@lanstar.com.br",
                    "PLATFORM",
                ),
            ),
            role_descriptions={"PLATFORM": "Cross-tenant platform administration"},
        )
        logger.info("seed completed successfully")
    finally:
        unbind_rls_bypass(bypass_token)
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
