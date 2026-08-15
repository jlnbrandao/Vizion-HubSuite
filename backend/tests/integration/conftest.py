"""Integration fixtures — real app, real Postgres, real Redis.

These tests exercise the HTTP surface end to end, so they need the dev stack and
a seeded database (`python -m scripts.seed`). When either is missing the whole
directory skips instead of failing, which keeps `pytest` usable without Docker.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.config.settings import get_settings
from src.main import create_app
from src.modules.roles.value_objects.role_name import RoleName
from src.modules.tenants.queries.tenant_queries import GetTenantBySlugQuery
from src.modules.users.commands.user_commands import CreateUserCommand, DeleteUserCommand
from src.shared.infrastructure.security.session_denylist import RedisSessionDenylist
from src.shared.infrastructure.tenant_context import (
    bind_rls_bypass,
    bind_tenant,
    unbind_rls_bypass,
    unbind_tenant,
)

UNIVERSE_HOST = "universe.localhost"
OWS_HOST = "ows.localhost"
SEED_PASSWORD = "123Mudar."


class _Unset:
    """Sentinel: "not probed yet" is distinct from "probed, all good" (None)."""


_UNSET = _Unset()


async def _postgres_reachable() -> str | None:
    import asyncpg

    settings = get_settings()
    dsn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    try:
        connection = await asyncpg.connect(dsn, timeout=3)
    except Exception as exc:  # noqa: BLE001 - any failure means "not available"
        return f"Postgres unavailable: {type(exc).__name__}"
    await connection.close()
    return None


async def _redis_reachable() -> str | None:
    from redis.asyncio import from_url

    client = from_url(get_settings().redis_url)
    try:
        await client.ping()
    except Exception as exc:  # noqa: BLE001
        return f"Redis unavailable: {type(exc).__name__}"
    finally:
        await client.aclose()
    return None


_HERE = Path(__file__).parent


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Mark tests of this directory as `integration` so `-m` selection works.

    The hook receives every collected item, not only the ones below this
    conftest, hence the path filter.
    """
    for item in items:
        if _HERE in Path(str(item.fspath)).parents:
            item.add_marker(pytest.mark.integration)


#: Probed once; the result is reused so only the first test pays for it.
_stack_status: str | None | _Unset = _UNSET


@pytest_asyncio.fixture(autouse=True)
async def require_stack() -> None:
    global _stack_status
    if _stack_status is _UNSET:
        _stack_status = await _postgres_reachable() or await _redis_reachable()
    if _stack_status:
        pytest.skip(_stack_status)


@pytest_asyncio.fixture(autouse=True)
async def reset_rate_limits() -> None:
    """Clear the shared Redis counters so tests don't rate-limit each other.

    The limiter is real and keyed by client IP; every test comes from the same
    address, and the auth window is deliberately small (20/min in production).
    """
    from redis.asyncio import from_url

    client = from_url(get_settings().redis_url)
    try:
        keys = [key async for key in client.scan_iter(match="rate:*")]
        if keys:
            await client.delete(*keys)
    finally:
        await client.aclose()


@pytest_asyncio.fixture
async def app() -> AsyncIterator[Any]:
    """Real application with its lifespan, so handlers and buses are registered.

    Function-scoped: the project pins the asyncio fixture loop scope to the test,
    and a session-wide engine cannot be shared across event loops.
    """
    application = create_app()
    async with application.router.lifespan_context(application):
        yield application


def _client(app: Any, host: str) -> AsyncClient:
    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url=f"http://{host}",
        headers={"Host": host},
    )


@pytest_asyncio.fixture
async def client(app: Any) -> AsyncIterator[AsyncClient]:
    """Client bound to the `universe` tenant."""
    async with _client(app, UNIVERSE_HOST) as http:
        yield http


@pytest_asyncio.fixture
async def platform_client(app: Any) -> AsyncIterator[AsyncClient]:
    """Client bound to the ops tenant `ows` (PLATFORM role lives there)."""
    async with _client(app, OWS_HOST) as http:
        yield http


async def login(http: AsyncClient, login_name: str, password: str = SEED_PASSWORD) -> str:
    """Log in and return the access token, skipping when the seed is missing."""
    response = await http.post(
        "/api/v1/auth/login", json={"login": login_name, "password": password}
    )
    if response.status_code == 401:
        pytest.skip(f"User '{login_name}' not available — run python -m scripts.seed")
    assert response.status_code == 200, response.text
    body = response.json()
    if body["mfa_required"]:
        pytest.skip(f"'{login_name}' has MFA enrolled; password login is not enough")
    return str(body["access_token"])


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


TEST_USER_PASSWORD = "Integr@tion1!"


@asynccontextmanager
async def provisioned_user(
    app: Any,
    *,
    tenant_slug: str,
    role_name: str,
    username: str,
) -> AsyncIterator[str]:
    """Create a throwaway user with one role and yield its email.

    Seed users are not usable for role-sensitive assertions: an operator may have
    enrolled MFA or changed their roles in the dev database. Provisioning here
    keeps each test's starting point explicit, and the user is removed afterwards.
    """
    container = app.state.container
    command_bus = container.command_bus()
    query_bus = container.query_bus()
    tenant = await query_bus.ask(GetTenantBySlugQuery(slug=tenant_slug))

    email = f"{username}@vizion.test"
    id_token, slug_token, name_token = bind_tenant(
        tenant.id, slug=tenant.slug, name=tenant.name
    )
    bypass = bind_rls_bypass(True)
    user_id: UUID | None = None
    try:
        roles = container.role_repository()
        async with container.unit_of_work():
            role = await roles.get_by_name(RoleName.from_primitive(role_name))
        assert role is not None, f"Role {role_name} missing — run python -m scripts.seed"

        user_id = await command_bus.execute(
            CreateUserCommand(
                tenant_id=tenant.id,
                email=email,
                username=username,
                full_name=f"Integration {role_name}",
                password=TEST_USER_PASSWORD,
                role_ids=frozenset({role.id}),
            )
        )
        yield email
    finally:
        if user_id is not None:
            await command_bus.execute(DeleteUserCommand(user_id=user_id))
        unbind_rls_bypass(bypass)
        unbind_tenant(id_token, slug_token, name_token)


@pytest_asyncio.fixture
async def admin_token(app: Any, client: AsyncClient) -> AsyncIterator[str]:
    async with provisioned_user(
        app, tenant_slug="universe", role_name="ADMIN", username="itest_admin"
    ) as email:
        yield await login(client, email, TEST_USER_PASSWORD)


@pytest_asyncio.fixture
async def viewer_token(app: Any, client: AsyncClient) -> AsyncIterator[str]:
    async with provisioned_user(
        app, tenant_slug="universe", role_name="VIEWER", username="itest_viewer"
    ) as email:
        yield await login(client, email, TEST_USER_PASSWORD)


@pytest_asyncio.fixture
async def platform_token(app: Any, platform_client: AsyncClient) -> AsyncIterator[str]:
    async with provisioned_user(
        app, tenant_slug="ows", role_name="PLATFORM", username="itest_platform"
    ) as email:
        yield await login(platform_client, email, TEST_USER_PASSWORD)


@pytest_asyncio.fixture
async def denylist(app: Any) -> AsyncIterator[RedisSessionDenylist]:
    """Session denylist of the running app, for revocation assertions."""
    yield app.state.container.session_denylist()
