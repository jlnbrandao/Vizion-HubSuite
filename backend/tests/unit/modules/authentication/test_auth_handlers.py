"""Handler tests for Authentication (login / refresh / logout)."""

from __future__ import annotations

import pytest

from src.config.settings import Settings
from src.modules.authentication.commands.auth_commands import (
    LoginCommand,
    LogoutCommand,
    RefreshTokenCommand,
)
from src.modules.authentication.handlers.auth_handlers import (
    LoginHandler,
    LogoutHandler,
    RefreshTokenHandler,
)
from src.modules.authentication.services.in_memory_refresh_token_store import (
    InMemoryRefreshTokenStore,
)
from src.modules.authentication.services.jwt_token_service import JwtTokenService
from src.modules.users.commands.user_commands import CreateUserCommand
from src.modules.users.handlers.user_handlers import (
    CreateUserHandler,
    GetUserByEmailHandler,
    GetUserByIdHandler,
    GetUserByUsernameHandler,
)
from src.modules.users.queries.user_queries import (
    GetUserByEmailQuery,
    GetUserByIdQuery,
    GetUserByUsernameQuery,
)
from src.modules.users.repositories.in_memory_user_repository import InMemoryUserRepository
from src.modules.users.services.password_hasher import PasswordHasher
from src.modules.users.value_objects.hashed_password import HashedPassword
from src.modules.users.value_objects.plain_password import PlainPassword
from src.shared.application.event_bus import EventBus
from src.shared.application.query_bus import QueryBus
from src.shared.infrastructure.exceptions import UnauthorizedError
from src.shared.infrastructure.security.session_denylist import InMemorySessionDenylist
from tests.unit.conftest import UNIVERSE_TENANT_ID
from tests.unit.shared.in_memory_unit_of_work import InMemoryUnitOfWork


class FakePasswordHasher(PasswordHasher):
    def hash(self, plain: PlainPassword) -> HashedPassword:
        return HashedPassword(value=f"hashed::{plain.value}::{'x' * 40}")

    def verify(self, plain: PlainPassword, hashed: HashedPassword) -> bool:
        return hashed.value == f"hashed::{plain.value}::{'x' * 40}"


@pytest.fixture
def settings() -> Settings:
    return Settings(
        jwt_secret_key="auth-test-secret-key-32-bytes-ok!",
        jwt_access_token_expire_minutes=15,
        jwt_refresh_token_expire_days=7,
    )


@pytest.fixture
def users_repo() -> InMemoryUserRepository:
    return InMemoryUserRepository()


@pytest.fixture
def event_bus() -> EventBus:
    return EventBus()


@pytest.fixture
def uow_factory(event_bus: EventBus):
    def factory() -> InMemoryUnitOfWork:
        return InMemoryUnitOfWork(event_bus)

    return factory


@pytest.fixture
def password_hasher() -> FakePasswordHasher:
    return FakePasswordHasher()


@pytest.fixture
def query_bus(uow_factory, users_repo) -> QueryBus:
    bus = QueryBus()
    bus.register(GetUserByEmailQuery, GetUserByEmailHandler(uow_factory, users_repo))
    bus.register(GetUserByUsernameQuery, GetUserByUsernameHandler(uow_factory, users_repo))
    bus.register(GetUserByIdQuery, GetUserByIdHandler(uow_factory, users_repo))
    return bus


@pytest.fixture
def token_service(settings: Settings) -> JwtTokenService:
    return JwtTokenService(settings)


@pytest.fixture
def refresh_store(settings: Settings) -> InMemoryRefreshTokenStore:
    return InMemoryRefreshTokenStore(settings)


@pytest.fixture
async def seeded_user(users_repo, uow_factory, password_hasher, query_bus):
    from src.modules.roles.handlers.role_handlers import CheckRolesExistHandler
    from src.modules.roles.queries.role_queries import CheckRolesExistQuery
    from src.modules.roles.repositories.in_memory_role_repository import InMemoryRoleRepository

    roles_repo = InMemoryRoleRepository()
    query_bus.register(
        CheckRolesExistQuery, CheckRolesExistHandler(uow_factory, roles_repo)
    )
    create = CreateUserHandler(uow_factory, users_repo, password_hasher, query_bus)
    user_id = await create.handle(
        CreateUserCommand(tenant_id=UNIVERSE_TENANT_ID,
            email="admin@lanstar.io",
            username="admin",
            full_name="Admin User",
            password="Secret123!",
        )
    )
    return user_id


@pytest.fixture
def login_handler(
    query_bus, password_hasher, token_service, refresh_store, event_bus, uow_factory, settings
):
    from types import SimpleNamespace
    from uuid import uuid4

    class FakeSessions:
        async def create(self, **kwargs):
            return uuid4()

        async def revoke(self, *args, **kwargs):
            return True

    class FakeMfa:
        async def has_confirmed_mfa(self, user_id):
            return False

        def issue_mfa_token(self, **kwargs):
            return "mfa-token"

    class FakePolicies:
        async def get_or_create(self):
            return SimpleNamespace(
                password_login_enabled=True,
                mfa_required="optional",
                max_failed_attempts=5,
                lockout_minutes=15,
            )

        async def assert_not_locked(self, user_id):
            return None

        async def record_failed_login(self, user_id, policy):
            return None

        async def clear_failed_login(self, user_id):
            return None

    return LoginHandler(
        query_bus,
        password_hasher,
        token_service,
        refresh_store,
        event_bus,
        uow_factory,
        FakeSessions(),
        FakeMfa(),
        FakePolicies(),
        settings,
    )


@pytest.fixture
def session_denylist() -> InMemorySessionDenylist:
    return InMemorySessionDenylist()


@pytest.fixture
def logout_handler(refresh_store, event_bus, uow_factory, session_denylist):
    class FakeSessions:
        async def revoke(self, *args, **kwargs):
            return True

    return LogoutHandler(
        refresh_store, event_bus, uow_factory, FakeSessions(), session_denylist
    )


@pytest.fixture
def refresh_handler(token_service, refresh_store, event_bus, query_bus, uow_factory, settings):
    from uuid import uuid4

    class FakeSessions:
        async def create(self, **kwargs):
            return uuid4()

    return RefreshTokenHandler(
        token_service,
        refresh_store,
        event_bus,
        query_bus,
        uow_factory,
        FakeSessions(),
        settings,
    )


@pytest.mark.asyncio
async def test_login_success_with_email(seeded_user, login_handler, token_service) -> None:
    pair = await login_handler.handle(
        LoginCommand(login="admin@lanstar.io", password="Secret123!")
    )
    assert pair.email == "admin@lanstar.io"
    assert pair.user_id == seeded_user
    claims = token_service.decode_access_token(pair.access_token)
    assert claims.user_id == seeded_user
    assert claims.sid is not None
    assert len(pair.refresh_token) >= 32


@pytest.mark.asyncio
async def test_login_success_with_username(seeded_user, login_handler) -> None:
    pair = await login_handler.handle(LoginCommand(login="admin", password="Secret123!"))
    assert pair.email == "admin@lanstar.io"
    assert pair.user_id == seeded_user


@pytest.mark.asyncio
async def test_login_username_is_case_insensitive(seeded_user, login_handler) -> None:
    pair = await login_handler.handle(LoginCommand(login="Admin", password="Secret123!"))
    assert pair.user_id == seeded_user


@pytest.mark.asyncio
async def test_login_wrong_password(seeded_user, login_handler) -> None:
    with pytest.raises(UnauthorizedError, match="Invalid credentials"):
        await login_handler.handle(
            LoginCommand(login="admin@lanstar.io", password="WrongPass1")
        )


@pytest.mark.asyncio
async def test_login_unknown_user(login_handler) -> None:
    with pytest.raises(UnauthorizedError, match="Invalid credentials"):
        await login_handler.handle(
            LoginCommand(login="nobody@lanstar.io", password="Secret123!")
        )


@pytest.mark.asyncio
async def test_refresh_rotates_token(
    seeded_user, login_handler, refresh_handler, refresh_store
) -> None:
    pair = await login_handler.handle(
        LoginCommand(login="admin", password="Secret123!")
    )
    old_refresh = pair.refresh_token

    new_pair = await refresh_handler.handle(
        RefreshTokenCommand(refresh_token=old_refresh)
    )
    assert new_pair.refresh_token != old_refresh
    assert new_pair.user_id == seeded_user

    with pytest.raises(UnauthorizedError):
        await refresh_handler.handle(RefreshTokenCommand(refresh_token=old_refresh))


@pytest.mark.asyncio
async def test_logout_invalidates_refresh(
    seeded_user, login_handler, logout_handler, refresh_handler
) -> None:
    pair = await login_handler.handle(
        LoginCommand(login="admin@lanstar.io", password="Secret123!")
    )
    await logout_handler.handle(LogoutCommand(refresh_token=pair.refresh_token))

    with pytest.raises(UnauthorizedError):
        await refresh_handler.handle(
            RefreshTokenCommand(refresh_token=pair.refresh_token)
        )


@pytest.mark.asyncio
async def test_refresh_reloads_role_ids_from_db(
    seeded_user, login_handler, refresh_handler, refresh_store, users_repo, uow_factory
) -> None:
    from uuid import uuid4

    from src.modules.authentication.value_objects.refresh_token import RefreshToken

    pair = await login_handler.handle(LoginCommand(login="admin", password="Secret123!"))
    new_role_id = uuid4()

    async with uow_factory() as uow:
        user = await users_repo.get_by_id(seeded_user)
        assert user is not None
        user.replace_roles({new_role_id})
        await users_repo.update(user)
        uow.track(user)
        await uow.commit()

    new_pair = await refresh_handler.handle(
        RefreshTokenCommand(refresh_token=pair.refresh_token)
    )
    stored = await refresh_store.get(
        RefreshToken.from_primitive(new_pair.refresh_token)
    )
    assert stored is not None
    assert stored.role_ids == (new_role_id,)


@pytest.mark.asyncio
async def test_logout_denylists_the_session(
    seeded_user, login_handler, logout_handler, session_denylist, token_service
) -> None:
    pair = await login_handler.handle(LoginCommand(login="admin", password="Secret123!"))
    claims = token_service.decode_access_token(pair.access_token)
    assert claims.sid is not None
    assert not await session_denylist.is_revoked(claims.sid)

    await logout_handler.handle(LogoutCommand(refresh_token=pair.refresh_token))

    assert await session_denylist.is_revoked(claims.sid)


@pytest.mark.asyncio
async def test_refresh_rejects_inactive_user(
    seeded_user, login_handler, refresh_handler, users_repo, uow_factory
) -> None:
    pair = await login_handler.handle(LoginCommand(login="admin", password="Secret123!"))

    async with uow_factory() as uow:
        user = await users_repo.get_by_id(seeded_user)
        assert user is not None
        user.deactivate()
        await users_repo.update(user)
        uow.track(user)
        await uow.commit()

    with pytest.raises(UnauthorizedError):
        await refresh_handler.handle(
            RefreshTokenCommand(refresh_token=pair.refresh_token)
        )
