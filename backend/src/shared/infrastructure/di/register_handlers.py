"""Registers CommandBus / QueryBus handlers for all Vertical Slice modules."""

from __future__ import annotations

from src.modules.authentication.commands.auth_commands import (
    LoginCommand,
    LogoutCommand,
    RefreshTokenCommand,
)
from src.modules.authentication.queries.access_queries import ResolveEffectiveAccessQuery
from src.modules.dashboard.queries.dashboard_queries import GetDashboardQuery
from src.modules.permissions.commands.permission_commands import (
    CreatePermissionCommand,
    DeletePermissionCommand,
    UpdatePermissionCommand,
)
from src.modules.permissions.queries.permission_queries import (
    CheckPermissionsExistQuery,
    CountPermissionsQuery,
    GetPermissionByIdQuery,
    GetPermissionsByIdsQuery,
    ListPermissionsQuery,
)
from src.modules.roles.commands.role_commands import (
    AssignPermissionsToRoleCommand,
    CreateRoleCommand,
    DeleteRoleCommand,
    ReplaceRolePermissionsCommand,
    RevokePermissionsFromRoleCommand,
    UpdateRoleCommand,
)
from src.modules.roles.queries.role_queries import (
    CheckRolesExistQuery,
    CountRolesQuery,
    GetRoleByIdQuery,
    GetRolesByIdsQuery,
    ListRolesQuery,
)
from src.modules.tenants.commands.tenant_commands import UpsertTenantCommand
from src.modules.tenants.queries.tenant_queries import GetTenantBySlugQuery
from src.modules.users.commands.user_commands import (
    AssignRolesToUserCommand,
    ChangeUserPasswordCommand,
    CreateUserCommand,
    DeleteUserCommand,
    ReplaceUserRolesCommand,
    RevokeRolesFromUserCommand,
    UpdateUserCommand,
)
from src.modules.users.queries.user_queries import (
    CountUsersQuery,
    GetUserByEmailQuery,
    GetUserByIdQuery,
    GetUserByUsernameQuery,
    ListUsersQuery,
)
from src.shared.application.command_bus import CommandBus
from src.shared.application.query_bus import QueryBus
from src.shared.infrastructure.di.container import Container


def register_module_handlers(container: Container) -> None:
    command_bus: CommandBus = container.command_bus()
    query_bus: QueryBus = container.query_bus()

    # Permissions
    command_bus.register(CreatePermissionCommand, container.create_permission_handler())
    command_bus.register(UpdatePermissionCommand, container.update_permission_handler())
    command_bus.register(DeletePermissionCommand, container.delete_permission_handler())
    query_bus.register(GetPermissionByIdQuery, container.get_permission_by_id_handler())
    query_bus.register(ListPermissionsQuery, container.list_permissions_handler())
    query_bus.register(CheckPermissionsExistQuery, container.check_permissions_exist_handler())
    query_bus.register(GetPermissionsByIdsQuery, container.get_permissions_by_ids_handler())
    query_bus.register(CountPermissionsQuery, container.count_permissions_handler())

    # Roles
    command_bus.register(CreateRoleCommand, container.create_role_handler())
    command_bus.register(UpdateRoleCommand, container.update_role_handler())
    command_bus.register(DeleteRoleCommand, container.delete_role_handler())
    command_bus.register(
        AssignPermissionsToRoleCommand, container.assign_permissions_to_role_handler()
    )
    command_bus.register(
        RevokePermissionsFromRoleCommand, container.revoke_permissions_from_role_handler()
    )
    command_bus.register(
        ReplaceRolePermissionsCommand, container.replace_role_permissions_handler()
    )
    query_bus.register(GetRoleByIdQuery, container.get_role_by_id_handler())
    query_bus.register(ListRolesQuery, container.list_roles_handler())
    query_bus.register(CheckRolesExistQuery, container.check_roles_exist_handler())
    query_bus.register(GetRolesByIdsQuery, container.get_roles_by_ids_handler())
    query_bus.register(CountRolesQuery, container.count_roles_handler())

    # Users
    command_bus.register(CreateUserCommand, container.create_user_handler())
    command_bus.register(UpdateUserCommand, container.update_user_handler())
    command_bus.register(ChangeUserPasswordCommand, container.change_user_password_handler())
    command_bus.register(DeleteUserCommand, container.delete_user_handler())
    command_bus.register(AssignRolesToUserCommand, container.assign_roles_to_user_handler())
    command_bus.register(RevokeRolesFromUserCommand, container.revoke_roles_from_user_handler())
    command_bus.register(ReplaceUserRolesCommand, container.replace_user_roles_handler())
    query_bus.register(GetUserByIdQuery, container.get_user_by_id_handler())
    query_bus.register(GetUserByEmailQuery, container.get_user_by_email_handler())
    query_bus.register(GetUserByUsernameQuery, container.get_user_by_username_handler())
    query_bus.register(ListUsersQuery, container.list_users_handler())
    query_bus.register(CountUsersQuery, container.count_users_handler())

    # Tenants
    command_bus.register(UpsertTenantCommand, container.upsert_tenant_handler())
    query_bus.register(GetTenantBySlugQuery, container.get_tenant_by_slug_handler())

    # Authentication
    command_bus.register(LoginCommand, container.login_handler())
    command_bus.register(LogoutCommand, container.logout_handler())
    command_bus.register(RefreshTokenCommand, container.refresh_token_handler())
    query_bus.register(
        ResolveEffectiveAccessQuery, container.resolve_effective_access_handler()
    )

    # Dashboard
    query_bus.register(GetDashboardQuery, container.get_dashboard_handler())
