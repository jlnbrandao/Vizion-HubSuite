"""Composition Root — Dependency Injection container.

All wiring happens here. Handlers receive dependencies; they never construct them.
"""

from __future__ import annotations

from dependency_injector import containers, providers
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from src.config.settings import Settings, get_settings
from src.modules.authentication.handlers.access_handlers import ResolveEffectiveAccessHandler
from src.modules.authentication.handlers.auth_handlers import (
    LoginHandler,
    LogoutHandler,
    RefreshTokenHandler,
)
from src.modules.authentication.services.jose_token_service import JoseTokenService
from src.modules.authentication.services.redis_refresh_token_store import RedisRefreshTokenStore
from src.modules.dashboard.handlers.dashboard_handlers import GetDashboardHandler
from src.modules.dashboard.providers.admin_provider import AdminDashboardProvider
from src.modules.dashboard.providers.client_provider import ClientDashboardProvider
from src.modules.dashboard.providers.manager_provider import ManagerDashboardProvider
from src.modules.dashboard.providers.operator_provider import OperatorDashboardProvider
from src.modules.dashboard.providers.viewer_provider import ViewerDashboardProvider
from src.modules.dashboard.services.dashboard_composer import DashboardComposer
from src.modules.permissions.handlers.permission_handlers import (
    CheckPermissionsExistHandler,
    CountPermissionsHandler,
    CreatePermissionHandler,
    DeletePermissionHandler,
    GetPermissionByIdHandler,
    GetPermissionsByIdsHandler,
    ListPermissionsHandler,
    UpdatePermissionHandler,
)
from src.modules.permissions.repositories.sqlalchemy_permission_repository import (
    SqlAlchemyPermissionRepository,
)
from src.modules.roles.handlers.role_handlers import (
    AssignPermissionsToRoleHandler,
    CheckRolesExistHandler,
    CountRolesHandler,
    CreateRoleHandler,
    DeleteRoleHandler,
    GetRoleByIdHandler,
    GetRolesByIdsHandler,
    ListRolesHandler,
    ReplaceRolePermissionsHandler,
    RevokePermissionsFromRoleHandler,
    UpdateRoleHandler,
)
from src.modules.roles.repositories.sqlalchemy_role_repository import SqlAlchemyRoleRepository
from src.modules.tenants.handlers.tenant_handlers import (
    GetTenantBySlugHandler,
    UpsertTenantHandler,
)
from src.modules.tenants.repositories.sqlalchemy_tenant_repository import (
    SqlAlchemyTenantRepository,
)
from src.modules.users.handlers.user_handlers import (
    AssignRolesToUserHandler,
    ChangeUserPasswordHandler,
    CountUsersHandler,
    CreateUserHandler,
    DeleteUserHandler,
    GetUserByEmailHandler,
    GetUserByIdHandler,
    GetUserByUsernameHandler,
    ListUsersHandler,
    ReplaceUserRolesHandler,
    RevokeRolesFromUserHandler,
    UpdateUserHandler,
)
from src.modules.users.repositories.sqlalchemy_user_repository import SqlAlchemyUserRepository
from src.modules.users.services.bcrypt_password_hasher import BcryptPasswordHasher
from src.shared.application.command_bus import CommandBus
from src.shared.application.event_bus import EventBus
from src.shared.application.query_bus import QueryBus
from src.shared.infrastructure.database import create_engine, create_session_factory
from src.shared.infrastructure.redis import create_redis_client
from src.shared.infrastructure.security.rate_limiter import RedisRateLimiter
from src.shared.infrastructure.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork


class Container(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(
        modules=[
            "src.modules.permissions.routes.permission_routes",
            "src.modules.roles.routes.role_routes",
            "src.modules.users.routes.user_routes",
            "src.modules.authentication.routes.auth_routes",
            "src.modules.dashboard.routes.dashboard_routes",
            "src.shared.infrastructure.security.dependencies",
        ],
    )

    config: providers.Singleton[Settings] = providers.Singleton(get_settings)

    engine: providers.Singleton[AsyncEngine] = providers.Singleton(
        create_engine,
        database_url=config.provided.database_url,
        echo=config.provided.app_debug,
    )

    session_factory: providers.Singleton[async_sessionmaker[AsyncSession]] = providers.Singleton(
        create_session_factory,
        engine=engine,
    )

    redis: providers.Singleton[Redis] = providers.Singleton(
        create_redis_client,
        redis_url=config.provided.redis_url,
    )

    event_bus: providers.Singleton[EventBus] = providers.Singleton(EventBus)
    command_bus: providers.Singleton[CommandBus] = providers.Singleton(CommandBus)
    query_bus: providers.Singleton[QueryBus] = providers.Singleton(QueryBus)

    unit_of_work: providers.Factory[SqlAlchemyUnitOfWork] = providers.Factory(
        SqlAlchemyUnitOfWork,
        session_factory=session_factory,
        event_bus=event_bus,
    )

    password_hasher: providers.Singleton[BcryptPasswordHasher] = providers.Singleton(
        BcryptPasswordHasher
    )

    token_service: providers.Singleton[JoseTokenService] = providers.Singleton(
        JoseTokenService,
        settings=config,
    )

    refresh_token_store: providers.Singleton[RedisRefreshTokenStore] = providers.Singleton(
        RedisRefreshTokenStore,
        redis=redis,
        settings=config,
    )

    rate_limiter: providers.Singleton[RedisRateLimiter] = providers.Singleton(
        RedisRateLimiter,
        redis=redis,
        settings=config,
    )

    # --- Repositories (session via ContextVar bound by UoW) ---
    permission_repository: providers.Singleton[SqlAlchemyPermissionRepository] = providers.Singleton(
        SqlAlchemyPermissionRepository
    )
    role_repository: providers.Singleton[SqlAlchemyRoleRepository] = providers.Singleton(
        SqlAlchemyRoleRepository
    )
    user_repository: providers.Singleton[SqlAlchemyUserRepository] = providers.Singleton(
        SqlAlchemyUserRepository
    )
    tenant_repository: providers.Singleton[SqlAlchemyTenantRepository] = providers.Singleton(
        SqlAlchemyTenantRepository
    )

    # --- Permission handlers ---
    create_permission_handler: providers.Factory[CreatePermissionHandler] = providers.Factory(
        CreatePermissionHandler,
        uow_factory=unit_of_work.provider,
        permissions=permission_repository,
    )
    update_permission_handler: providers.Factory[UpdatePermissionHandler] = providers.Factory(
        UpdatePermissionHandler,
        uow_factory=unit_of_work.provider,
        permissions=permission_repository,
    )
    delete_permission_handler: providers.Factory[DeletePermissionHandler] = providers.Factory(
        DeletePermissionHandler,
        uow_factory=unit_of_work.provider,
        permissions=permission_repository,
    )
    get_permission_by_id_handler: providers.Factory[GetPermissionByIdHandler] = providers.Factory(
        GetPermissionByIdHandler,
        uow_factory=unit_of_work.provider,
        permissions=permission_repository,
    )
    list_permissions_handler: providers.Factory[ListPermissionsHandler] = providers.Factory(
        ListPermissionsHandler,
        uow_factory=unit_of_work.provider,
        permissions=permission_repository,
    )
    check_permissions_exist_handler: providers.Factory[CheckPermissionsExistHandler] = (
        providers.Factory(
            CheckPermissionsExistHandler,
            uow_factory=unit_of_work.provider,
            permissions=permission_repository,
        )
    )
    get_permissions_by_ids_handler: providers.Factory[GetPermissionsByIdsHandler] = (
        providers.Factory(
            GetPermissionsByIdsHandler,
            uow_factory=unit_of_work.provider,
            permissions=permission_repository,
        )
    )
    count_permissions_handler: providers.Factory[CountPermissionsHandler] = providers.Factory(
        CountPermissionsHandler,
        uow_factory=unit_of_work.provider,
        permissions=permission_repository,
    )

    # --- Role handlers ---
    create_role_handler: providers.Factory[CreateRoleHandler] = providers.Factory(
        CreateRoleHandler,
        uow_factory=unit_of_work.provider,
        roles=role_repository,
    )
    update_role_handler: providers.Factory[UpdateRoleHandler] = providers.Factory(
        UpdateRoleHandler,
        uow_factory=unit_of_work.provider,
        roles=role_repository,
    )
    delete_role_handler: providers.Factory[DeleteRoleHandler] = providers.Factory(
        DeleteRoleHandler,
        uow_factory=unit_of_work.provider,
        roles=role_repository,
    )
    assign_permissions_to_role_handler: providers.Factory[AssignPermissionsToRoleHandler] = (
        providers.Factory(
            AssignPermissionsToRoleHandler,
            uow_factory=unit_of_work.provider,
            roles=role_repository,
            query_bus=query_bus,
        )
    )
    revoke_permissions_from_role_handler: providers.Factory[RevokePermissionsFromRoleHandler] = (
        providers.Factory(
            RevokePermissionsFromRoleHandler,
            uow_factory=unit_of_work.provider,
            roles=role_repository,
        )
    )
    replace_role_permissions_handler: providers.Factory[ReplaceRolePermissionsHandler] = (
        providers.Factory(
            ReplaceRolePermissionsHandler,
            uow_factory=unit_of_work.provider,
            roles=role_repository,
            query_bus=query_bus,
        )
    )
    get_role_by_id_handler: providers.Factory[GetRoleByIdHandler] = providers.Factory(
        GetRoleByIdHandler,
        uow_factory=unit_of_work.provider,
        roles=role_repository,
    )
    list_roles_handler: providers.Factory[ListRolesHandler] = providers.Factory(
        ListRolesHandler,
        uow_factory=unit_of_work.provider,
        roles=role_repository,
    )
    check_roles_exist_handler: providers.Factory[CheckRolesExistHandler] = providers.Factory(
        CheckRolesExistHandler,
        uow_factory=unit_of_work.provider,
        roles=role_repository,
    )
    get_roles_by_ids_handler: providers.Factory[GetRolesByIdsHandler] = providers.Factory(
        GetRolesByIdsHandler,
        uow_factory=unit_of_work.provider,
        roles=role_repository,
    )
    count_roles_handler: providers.Factory[CountRolesHandler] = providers.Factory(
        CountRolesHandler,
        uow_factory=unit_of_work.provider,
        roles=role_repository,
    )

    # --- User handlers ---
    create_user_handler: providers.Factory[CreateUserHandler] = providers.Factory(
        CreateUserHandler,
        uow_factory=unit_of_work.provider,
        users=user_repository,
        password_hasher=password_hasher,
        query_bus=query_bus,
    )
    update_user_handler: providers.Factory[UpdateUserHandler] = providers.Factory(
        UpdateUserHandler,
        uow_factory=unit_of_work.provider,
        users=user_repository,
        refresh_store=refresh_token_store,
    )
    change_user_password_handler: providers.Factory[ChangeUserPasswordHandler] = providers.Factory(
        ChangeUserPasswordHandler,
        uow_factory=unit_of_work.provider,
        users=user_repository,
        password_hasher=password_hasher,
        refresh_store=refresh_token_store,
    )
    delete_user_handler: providers.Factory[DeleteUserHandler] = providers.Factory(
        DeleteUserHandler,
        uow_factory=unit_of_work.provider,
        users=user_repository,
        refresh_store=refresh_token_store,
    )
    assign_roles_to_user_handler: providers.Factory[AssignRolesToUserHandler] = providers.Factory(
        AssignRolesToUserHandler,
        uow_factory=unit_of_work.provider,
        users=user_repository,
        query_bus=query_bus,
        refresh_store=refresh_token_store,
    )
    revoke_roles_from_user_handler: providers.Factory[RevokeRolesFromUserHandler] = (
        providers.Factory(
            RevokeRolesFromUserHandler,
            uow_factory=unit_of_work.provider,
            users=user_repository,
            refresh_store=refresh_token_store,
        )
    )
    replace_user_roles_handler: providers.Factory[ReplaceUserRolesHandler] = providers.Factory(
        ReplaceUserRolesHandler,
        uow_factory=unit_of_work.provider,
        users=user_repository,
        query_bus=query_bus,
        refresh_store=refresh_token_store,
    )
    get_user_by_id_handler: providers.Factory[GetUserByIdHandler] = providers.Factory(
        GetUserByIdHandler,
        uow_factory=unit_of_work.provider,
        users=user_repository,
    )
    get_user_by_email_handler: providers.Factory[GetUserByEmailHandler] = providers.Factory(
        GetUserByEmailHandler,
        uow_factory=unit_of_work.provider,
        users=user_repository,
    )
    get_user_by_username_handler: providers.Factory[GetUserByUsernameHandler] = providers.Factory(
        GetUserByUsernameHandler,
        uow_factory=unit_of_work.provider,
        users=user_repository,
    )
    list_users_handler: providers.Factory[ListUsersHandler] = providers.Factory(
        ListUsersHandler,
        uow_factory=unit_of_work.provider,
        users=user_repository,
    )
    count_users_handler: providers.Factory[CountUsersHandler] = providers.Factory(
        CountUsersHandler,
        uow_factory=unit_of_work.provider,
        users=user_repository,
    )

    # --- Tenant handlers ---
    get_tenant_by_slug_handler: providers.Factory[GetTenantBySlugHandler] = providers.Factory(
        GetTenantBySlugHandler,
        uow_factory=unit_of_work.provider,
        tenants=tenant_repository,
    )
    upsert_tenant_handler: providers.Factory[UpsertTenantHandler] = providers.Factory(
        UpsertTenantHandler,
        uow_factory=unit_of_work.provider,
        tenants=tenant_repository,
    )

    # --- Authentication handlers ---
    login_handler: providers.Factory[LoginHandler] = providers.Factory(
        LoginHandler,
        query_bus=query_bus,
        password_hasher=password_hasher,
        token_service=token_service,
        refresh_store=refresh_token_store,
        event_bus=event_bus,
    )
    logout_handler: providers.Factory[LogoutHandler] = providers.Factory(
        LogoutHandler,
        refresh_store=refresh_token_store,
        event_bus=event_bus,
    )
    refresh_token_handler: providers.Factory[RefreshTokenHandler] = providers.Factory(
        RefreshTokenHandler,
        token_service=token_service,
        refresh_store=refresh_token_store,
        event_bus=event_bus,
        query_bus=query_bus,
    )
    resolve_effective_access_handler: providers.Factory[ResolveEffectiveAccessHandler] = (
        providers.Factory(
            ResolveEffectiveAccessHandler,
            query_bus=query_bus,
        )
    )

    # --- Dashboard ---
    admin_dashboard_provider: providers.Singleton[AdminDashboardProvider] = providers.Singleton(
        AdminDashboardProvider,
        query_bus=query_bus,
    )
    manager_dashboard_provider: providers.Singleton[ManagerDashboardProvider] = (
        providers.Singleton(ManagerDashboardProvider)
    )
    operator_dashboard_provider: providers.Singleton[OperatorDashboardProvider] = (
        providers.Singleton(OperatorDashboardProvider)
    )
    client_dashboard_provider: providers.Singleton[ClientDashboardProvider] = providers.Singleton(
        ClientDashboardProvider,
        query_bus=query_bus,
    )
    viewer_dashboard_provider: providers.Singleton[ViewerDashboardProvider] = providers.Singleton(
        ViewerDashboardProvider
    )

    dashboard_composer: providers.Singleton[DashboardComposer] = providers.Singleton(
        DashboardComposer,
        providers=providers.List(
            admin_dashboard_provider,
            manager_dashboard_provider,
            operator_dashboard_provider,
            client_dashboard_provider,
            viewer_dashboard_provider,
        ),
    )

    get_dashboard_handler: providers.Factory[GetDashboardHandler] = providers.Factory(
        GetDashboardHandler,
        composer=dashboard_composer,
    )


def create_container() -> Container:
    return Container()
