"""`require_permission` must resolve the real AuthorizationService through DI.

Guards against the wiring regressing to an unresolved provider marker, which would
silently skip authorization.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from src.shared.infrastructure.di.container import create_container
from src.shared.infrastructure.exceptions import ForbiddenError
from src.shared.infrastructure.security.authorization import (
    AuthorizationService,
    NullAuthorizationAuditSink,
)
from src.shared.infrastructure.security.current_user import CurrentUser
from src.shared.infrastructure.security.dependencies import (
    get_current_user,
    require_permission,
)


def _app(user: CurrentUser) -> FastAPI:
    container = create_container()
    # Keep the denial path off the database in unit tests.
    container.authorization_audit_sink.override(NullAuthorizationAuditSink())
    container.wire(modules=["src.shared.infrastructure.security.dependencies"])

    app = FastAPI()
    app.state.container = container

    @app.get("/vehicles")
    async def list_vehicles(
        actor: CurrentUser = Depends(require_permission("vehicle.read")),
    ) -> dict[str, str]:
        return {"actor": str(actor.id)}

    @app.exception_handler(ForbiddenError)
    async def forbidden(_, exc: ForbiddenError):
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=403, content={"error": {"message": exc.message}})

    app.dependency_overrides[get_current_user] = lambda: user
    return app


def _user(*permissions: str) -> CurrentUser:
    return CurrentUser(
        id=uuid4(),
        email="u@x.com",
        full_name="User",
        tenant_id=uuid4(),
        tenant_slug="universe",
        tenant_name="Universe",
        role_names=frozenset({"OPERATOR"}),
        permissions=frozenset(permissions),
    )


async def _call(user: CurrentUser):
    transport = ASGITransport(app=_app(user))
    async with AsyncClient(transport=transport, base_url="http://universe.localhost") as client:
        return await client.get("/vehicles")


@pytest.mark.asyncio
async def test_permission_granted() -> None:
    response = await _call(_user("vehicle.read"))
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_permission_denied_by_engine() -> None:
    response = await _call(_user("vehicle.list"))
    assert response.status_code == 403
    assert "vehicle.read" in response.json()["error"]["message"]


@pytest.mark.asyncio
async def test_container_provides_a_real_engine() -> None:
    container = create_container()
    assert isinstance(container.authorization_service(), AuthorizationService)
