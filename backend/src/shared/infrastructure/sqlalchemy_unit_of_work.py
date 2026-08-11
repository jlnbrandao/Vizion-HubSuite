"""SQLAlchemy-backed Unit of Work.

Tracks Aggregate Roots, commits the session, then publishes Domain Events.
If commit fails, events are never published (consistency over delivery).

Applies Postgres RLS GUCs from tenant_context on enter:
  app.rls_bypass / app.current_tenant_id (SET LOCAL via set_config).
"""

from __future__ import annotations

from contextvars import Token
from types import TracebackType
from typing import Self

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.shared.application.event_bus import EventBus
from src.shared.application.unit_of_work import UnitOfWork
from src.shared.domain.aggregate_root import AggregateRoot
from src.shared.domain.domain_event import DomainEvent
from src.shared.infrastructure.session_context import bind_session, unbind_session
from src.shared.infrastructure.tenant_context import get_current_tenant_id, get_rls_bypass


class SqlAlchemyUnitOfWork(UnitOfWork):
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        event_bus: EventBus,
    ) -> None:
        self._session_factory = session_factory
        self._event_bus = event_bus
        self._session: AsyncSession | None = None
        self._tracked: list[AggregateRoot] = []
        self._session_token: Token[AsyncSession | None] | None = None

    @property
    def session(self) -> AsyncSession:
        if self._session is None:
            raise RuntimeError("UnitOfWork is not active. Use 'async with uow:'.")
        return self._session

    async def _apply_rls_gucs(self) -> None:
        assert self._session is not None
        bypass = "on" if get_rls_bypass() else "off"
        await self._session.execute(
            text("SELECT set_config('app.rls_bypass', :v, true)"),
            {"v": bypass},
        )
        tenant_id = get_current_tenant_id()
        if tenant_id is not None:
            await self._session.execute(
                text("SELECT set_config('app.current_tenant_id', :tid, true)"),
                {"tid": str(tenant_id)},
            )
        else:
            await self._session.execute(
                text("SELECT set_config('app.current_tenant_id', '', true)"),
            )

    async def __aenter__(self) -> Self:
        self._session = self._session_factory()
        self._session_token = bind_session(self._session)
        self._tracked = []
        await self._apply_rls_gucs()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()
        if self._session_token is not None:
            unbind_session(self._session_token)
            self._session_token = None
        if self._session is not None:
            await self._session.close()
            self._session = None
        self._tracked = []

    def track(self, aggregate: AggregateRoot) -> None:
        if aggregate not in self._tracked:
            self._tracked.append(aggregate)

    def collect_events(self) -> list[DomainEvent]:
        events: list[DomainEvent] = []
        for aggregate in self._tracked:
            events.extend(aggregate.pull_domain_events())
        return events

    async def commit(self) -> None:
        events = self.collect_events()
        await self.session.commit()
        await self._event_bus.publish_many(events)

    async def rollback(self) -> None:
        if self._session is not None:
            await self._session.rollback()
        self._tracked = []
