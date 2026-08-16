"""Composition root — the only place that chooses Local vs Hub adapters."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from openvizion.contracts.events import EventEnvelope
from openvizion.events.adapter import EventBusAdapter
from openvizion.events.factory import create_event_bus
from openvizion.events.local import LocalEventBus
from openvizion.kernel.audit import AuditProvider, AuditRecord
from openvizion.kernel.authorization import AuthorizationProvider
from openvizion.kernel.configuration import AdapterSelection
from openvizion.kernel.entitlements import EntitlementProvider
from openvizion.kernel.hub import HubPlatformAdapter
from openvizion.kernel.identity import Principal, TenantInfo
from openvizion.kernel.local import LocalPlatformAdapter
from openvizion.kernel.local_providers import LocalAuthorizationProvider, LocalEntitlementProvider
from openvizion.kernel.platform import PlatformAdapter

from tracking.config import Settings
from tracking.infrastructure.database.base import create_engine, create_session_factory
from tracking.infrastructure.database.models import (
    AuditEventModel,
    TenantEntitlementModel,
    TenantModel,
    UserModel,
)
from tracking.infrastructure.security.jwt import JwtService, permissions_for_role


@dataclass
class AppContainer:
    settings: Settings
    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]
    jwt: JwtService
    event_bus: EventBusAdapter
    platform: PlatformAdapter
    authorization: AuthorizationProvider
    entitlements: EntitlementProvider
    hub: HubPlatformAdapter | None


class SqlAuditProvider:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def record(self, entry: AuditRecord) -> None:
        async with self._session_factory() as session:
            session.add(
                AuditEventModel(
                    id=entry.id,
                    tenant_id=entry.tenant_id,
                    user_id=entry.user_id,
                    action=entry.action,
                    resource_type=entry.resource_type,
                    resource_id=entry.resource_id,
                    metadata_json=entry.metadata,
                    created_at=entry.occurred_at,
                )
            )
            await session.commit()


class SqlEntitlementProvider:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def has(self, tenant_id: UUID, capability: str) -> bool:
        async with self._session_factory() as session:
            result = await session.execute(
                select(TenantEntitlementModel).where(
                    TenantEntitlementModel.tenant_id == tenant_id,
                    TenantEntitlementModel.capability == capability,
                )
            )
            return result.scalar_one_or_none() is not None

    async def list_for_tenant(self, tenant_id: UUID) -> frozenset[str]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(TenantEntitlementModel.capability).where(
                    TenantEntitlementModel.tenant_id == tenant_id
                )
            )
            return frozenset(result.scalars().all())


class SqlUserLookup:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        jwt: JwtService,
    ) -> None:
        self._session_factory = session_factory
        self._jwt = jwt

    async def __call__(self, access_token: str) -> Principal:
        return self._jwt.decode(access_token)


class HubEntitlementProvider:
    def __init__(self, hub: HubPlatformAdapter) -> None:
        self._hub = hub

    async def has(self, tenant_id: UUID, capability: str) -> bool:
        return await self._hub.check_entitlement(tenant_id, capability)

    async def list_for_tenant(self, tenant_id: UUID) -> frozenset[str]:
        from tracking.permissions import CAPABILITY_ADVANCED_TELEMETRY, CAPABILITY_BASIC

        found: set[str] = set()
        for capability in (CAPABILITY_BASIC, CAPABILITY_ADVANCED_TELEMETRY, "tracking"):
            if await self.has(tenant_id, capability):
                found.add(capability)
        return frozenset(found)


class SqlTenantLookup:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def __call__(self, tenant_id: UUID) -> TenantInfo:
        async with self._session_factory() as session:
            row = await session.get(TenantModel, tenant_id)
            if row is None:
                raise KeyError(str(tenant_id))
            return TenantInfo(id=row.id, slug=row.slug, name=row.name, is_active=row.is_active)


def build_container(settings: Settings | None = None) -> AppContainer:
    settings = settings or Settings()
    settings.validate_mode()
    engine = create_engine(settings.database_url, echo=settings.app_debug)
    session_factory = create_session_factory(engine)
    jwt = JwtService(
        settings.jwt_secret_key,
        settings.jwt_algorithm,
        settings.jwt_access_token_expire_minutes,
    )
    if settings.event_bus_adapter == AdapterSelection.KAFKA:
        if not settings.kafka_bootstrap_servers.strip():
            raise ValueError("EVENT_BUS_ADAPTER=kafka requires KAFKA_BOOTSTRAP_SERVERS")
        try:
            from aiokafka import AIOKafkaProducer
        except ImportError as exc:  # pragma: no cover
            raise ValueError("EVENT_BUS_ADAPTER=kafka requires the aiokafka extra") from exc
        producer = AIOKafkaProducer(bootstrap_servers=settings.kafka_bootstrap_servers)
        event_bus = create_event_bus(
            AdapterSelection.KAFKA,
            kafka_producer=producer,
            topic_prefix=settings.kafka_topic_prefix,
        )
    else:
        event_bus = create_event_bus(
            AdapterSelection.LOCAL,
            topic_prefix=settings.kafka_topic_prefix,
        )
    authorization: AuthorizationProvider = LocalAuthorizationProvider()
    entitlements: EntitlementProvider = SqlEntitlementProvider(session_factory)
    audit: AuditProvider = SqlAuditProvider(session_factory)
    hub: HubPlatformAdapter | None = None

    async def publish(
        event_type: str,
        tenant_id: UUID,
        payload: dict,
        correlation_id: str | None,
    ) -> None:
        await event_bus.publish(
            EventEnvelope(
                event_type=event_type,
                tenant_id=tenant_id,
                payload=payload,
                correlation_id=correlation_id,
                producer=settings.service_name,
            )
        )

    if settings.platform_adapter == AdapterSelection.HUB:
        hub = HubPlatformAdapter(
            base_url=settings.platform_core_url,
            client_id=settings.platform_client_id,
            client_secret=settings.platform_client_secret,
            timeout_seconds=settings.platform_timeout_seconds,
        )
        platform: PlatformAdapter = hub
        entitlements = HubEntitlementProvider(hub)
    else:
        platform = LocalPlatformAdapter(
            user_lookup=SqlUserLookup(session_factory, jwt),
            tenant_lookup=SqlTenantLookup(session_factory),
            authorization=authorization,
            entitlements=entitlements,
            audit=audit,
            event_publisher=publish,
        )

    return AppContainer(
        settings=settings,
        engine=engine,
        session_factory=session_factory,
        jwt=jwt,
        event_bus=event_bus,
        platform=platform,
        authorization=authorization,
        entitlements=entitlements,
        hub=hub,
    )


async def load_principal_from_user_row(row: UserModel, tenant: TenantInfo) -> Principal:
    return Principal(
        id=row.id,
        email=row.email,
        full_name=row.full_name,
        tenant_id=row.tenant_id,
        tenant_slug=tenant.slug,
        tenant_name=tenant.name,
        role_names=frozenset({row.role_name}),
        permissions=permissions_for_role(row.role_name),
    )


def new_id() -> UUID:
    return uuid4()


def is_local_event_bus(bus: EventBusAdapter) -> bool:
    return isinstance(bus, LocalEventBus)
