"""Product instance registry and Hub product-facing APIs."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import httpx
import jwt
from pydantic import BaseModel, Field
from sqlalchemy import select

from src.config.settings import Settings
from src.modules.authentication.queries.access_queries import (
    EffectiveAccessDto,
    ResolveEffectiveAccessQuery,
)
from src.modules.iam.audit.service import AuditService
from src.modules.products.location import ENVIRONMENTS, build_url, parse_endpoint
from src.modules.products.models import ProductInstanceModel, TenantProductBindingModel
from src.modules.services.catalog import CORE_SERVICES, PRODUCT_SERVICES
from src.modules.services.service import ServiceCatalogService
from src.modules.tenants.repositories.tenant_model import TenantModel
from src.modules.users.dtos.user_dtos import UserDto
from src.modules.users.queries.user_queries import GetUserByIdQuery
from src.modules.users.services.password_hasher import PasswordHasher
from src.modules.users.value_objects.hashed_password import HashedPassword
from src.modules.users.value_objects.plain_password import PlainPassword
from src.shared.application.query_bus import QueryBus
from src.shared.infrastructure.exceptions import (
    ConflictError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)
from src.shared.infrastructure.security.authorization import AuthorizationService, RequestContext
from src.shared.infrastructure.security.current_user import CurrentUser
from src.shared.infrastructure.session_context import get_current_session
from src.shared.infrastructure.tenant_context import bind_tenant, unbind_tenant

_PRODUCT_SLUGS = frozenset({"tracking", "iot", "snmp", "gis", "lanstar"})
_SERVICE_TOKEN_MINUTES = 60


class BindingView(BaseModel):
    tenant_id: UUID
    tenant_slug: str = ""
    tenant_name: str = ""
    product_instance_id: UUID
    service_slug: str
    status: str


class ProductInstanceView(BaseModel):
    id: UUID
    slug: str
    name: str
    base_url: str
    ui_url: str | None = None
    status: str
    version: str
    client_id: str
    last_heartbeat_at: datetime | None = None
    environment: str = "local_docker"
    host: str = ""
    api_port: int | None = None
    ui_host: str | None = None
    ui_port: int | None = None
    scheme: str = "http"
    notes: str = ""
    bindings: list[BindingView] = Field(default_factory=list)


class HubLocationView(BaseModel):
    kind: str = "hub"
    name: str
    environment: str
    host: str
    api_port: int
    ui_port: int
    api_url: str
    ui_url: str
    services: list[str]
    notes: str = ""
    runtime: str = "in-process FastAPI"


class ProductSlugOption(BaseModel):
    slug: str
    name: str


class TopologyView(BaseModel):
    hub: HubLocationView
    instances: list[ProductInstanceView]
    product_options: list[ProductSlugOption] = Field(default_factory=list)


class CreateInstanceRequest(BaseModel):
    slug: str
    name: str
    client_id: str
    client_secret: str = Field(min_length=16)
    environment: str = "local_docker"
    host: str = ""
    api_port: int | None = None
    ui_host: str | None = None
    ui_port: int | None = None
    scheme: str = "http"
    base_url: str = ""
    ui_url: str | None = None
    notes: str = ""


class UpdateInstanceRequest(BaseModel):
    name: str | None = None
    environment: str | None = None
    host: str | None = None
    api_port: int | None = None
    ui_host: str | None = None
    ui_port: int | None = None
    scheme: str | None = None
    base_url: str | None = None
    ui_url: str | None = None
    notes: str | None = None
    status: str | None = None
    client_secret: str | None = None


class BindTenantBody(BaseModel):
    tenant_id: UUID
    status: str = "active"


class ProductRegistryService:
    def __init__(self, settings: Settings, password_hasher: PasswordHasher) -> None:
        self._settings = settings
        self._hasher = password_hasher

    async def list_instances(self) -> list[ProductInstanceView]:
        session = get_current_session()
        result = await session.execute(
            select(ProductInstanceModel).order_by(
                ProductInstanceModel.slug, ProductInstanceModel.name
            )
        )
        rows = list(result.scalars().all())
        bindings = await self._bindings_map([row.id for row in rows])
        return [self._to_view(row, bindings.get(row.id, [])) for row in rows]

    async def get(self, instance_id: UUID) -> ProductInstanceView:
        row = await self._require(instance_id)
        bindings = await self._bindings_map([row.id])
        return self._to_view(row, bindings.get(row.id, []))

    async def topology(self) -> TopologyView:
        settings = self._settings
        host = settings.hub_public_host.strip() or "localhost"
        env = settings.hub_environment.strip().lower() or "local_docker"
        if env not in ENVIRONMENTS:
            env = "local_docker"
        scheme = "http" if settings.is_development else "https"
        return TopologyView(
            hub=HubLocationView(
                name=settings.app_name,
                environment=env,
                host=host,
                api_port=settings.hub_public_api_port,
                ui_port=settings.hub_public_ui_port,
                api_url=build_url(scheme, host, settings.hub_public_api_port),
                ui_url=build_url(scheme, host, settings.hub_public_ui_port),
                services=[item.slug for item in CORE_SERVICES],
                notes=settings.hub_notes.strip(),
            ),
            instances=await self.list_instances(),
            product_options=[
                ProductSlugOption(slug=item.slug, name=item.name) for item in PRODUCT_SERVICES
            ],
        )

    async def create(self, body: CreateInstanceRequest) -> ProductInstanceView:
        if body.slug not in _PRODUCT_SLUGS:
            raise ValidationError(f"Unknown product slug: {body.slug}")
        location = self._resolve_location(
            environment=body.environment,
            host=body.host,
            api_port=body.api_port,
            ui_host=body.ui_host,
            ui_port=body.ui_port,
            scheme=body.scheme,
            base_url=body.base_url,
            ui_url=body.ui_url,
            notes=body.notes,
        )
        session = get_current_session()
        existing = await session.execute(
            select(ProductInstanceModel).where(ProductInstanceModel.client_id == body.client_id)
        )
        if existing.scalar_one_or_none() is not None:
            raise ConflictError("client_id already registered")
        hashed = self._hasher.hash(PlainPassword.from_login_attempt(body.client_secret))
        row = ProductInstanceModel(
            id=uuid4(),
            slug=body.slug,
            name=body.name.strip(),
            base_url=location["base_url"],
            ui_url=location["ui_url"],
            status="registered",
            version="",
            client_id=body.client_id.strip(),
            client_secret_hash=hashed.value,
            environment=location["environment"],
            host=location["host"],
            api_port=location["api_port"],
            ui_host=location["ui_host"],
            ui_port=location["ui_port"],
            scheme=location["scheme"],
            notes=location["notes"],
        )
        session.add(row)
        await session.flush()
        return self._to_view(row)

    async def update(self, instance_id: UUID, body: UpdateInstanceRequest) -> ProductInstanceView:
        row = await self._require(instance_id)
        if body.name is not None:
            row.name = body.name.strip()
        if body.status is not None:
            row.status = body.status
        if body.client_secret:
            row.client_secret_hash = self._hasher.hash(
                PlainPassword.from_login_attempt(body.client_secret)
            ).value
        location = self._resolve_location(
            environment=body.environment if body.environment is not None else row.environment,
            host=body.host if body.host is not None else row.host,
            api_port=body.api_port if body.api_port is not None else row.api_port,
            ui_host=body.ui_host if body.ui_host is not None else row.ui_host,
            ui_port=body.ui_port if body.ui_port is not None else row.ui_port,
            scheme=body.scheme if body.scheme is not None else row.scheme,
            base_url=body.base_url if body.base_url is not None else row.base_url,
            ui_url=body.ui_url if body.ui_url is not None else row.ui_url,
            notes=body.notes if body.notes is not None else row.notes,
        )
        row.environment = location["environment"]
        row.host = location["host"]
        row.api_port = location["api_port"]
        row.ui_host = location["ui_host"]
        row.ui_port = location["ui_port"]
        row.scheme = location["scheme"]
        row.base_url = location["base_url"]
        row.ui_url = location["ui_url"]
        row.notes = location["notes"]
        return self._to_view(row)

    async def deactivate(self, instance_id: UUID) -> None:
        row = await self._require(instance_id)
        row.status = "disabled"

    async def probe(self, instance_id: UUID) -> dict[str, Any]:
        row = await self._require(instance_id)
        url = f"{row.base_url}/ready"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                ready = await client.get(url)
                version = await client.get(f"{row.base_url}/version")
        except httpx.HTTPError as exc:
            return {"ok": False, "error": str(exc)}
        version_body: dict[str, Any] = {}
        if version.status_code < 400:
            try:
                version_body = version.json()
                row.version = str(version_body.get("version") or row.version)
            except ValueError:
                version_body = {}
        return {
            "ok": ready.status_code < 400,
            "ready_status": ready.status_code,
            "version": version_body,
        }

    async def list_bindings(self, instance_id: UUID) -> list[BindingView]:
        await self._require(instance_id)
        mapped = await self._bindings_map([instance_id])
        return mapped.get(instance_id, [])

    async def bind_tenant(self, instance_id: UUID, body: BindTenantBody) -> BindingView:
        row = await self._require(instance_id)
        session = get_current_session()
        existing = await session.execute(
            select(TenantProductBindingModel).where(
                TenantProductBindingModel.product_instance_id == instance_id,
                TenantProductBindingModel.tenant_id == body.tenant_id,
            )
        )
        current = existing.scalar_one_or_none()
        if current is None:
            current = TenantProductBindingModel(
                id=uuid4(),
                tenant_id=body.tenant_id,
                product_instance_id=instance_id,
                service_slug=row.slug,
                status=body.status,
            )
            session.add(current)
        else:
            current.status = body.status
        await session.flush()
        tenant = await session.get(TenantModel, current.tenant_id)
        return BindingView(
            tenant_id=current.tenant_id,
            tenant_slug=tenant.slug if tenant else "",
            tenant_name=tenant.name if tenant else "",
            product_instance_id=current.product_instance_id,
            service_slug=current.service_slug,
            status=current.status,
        )

    async def _require(self, instance_id: UUID) -> ProductInstanceModel:
        row = await get_current_session().get(ProductInstanceModel, instance_id)
        if row is None:
            raise NotFoundError("Product instance not found")
        return row

    async def _bindings_map(self, instance_ids: list[UUID]) -> dict[UUID, list[BindingView]]:
        if not instance_ids:
            return {}
        session = get_current_session()
        result = await session.execute(
            select(TenantProductBindingModel).where(
                TenantProductBindingModel.product_instance_id.in_(instance_ids)
            )
        )
        rows = list(result.scalars().all())
        tenant_ids = {row.tenant_id for row in rows}
        tenants: dict[UUID, TenantModel] = {}
        if tenant_ids:
            tenant_rows = await session.execute(
                select(TenantModel).where(TenantModel.id.in_(tenant_ids))
            )
            tenants = {item.id: item for item in tenant_rows.scalars().all()}
        grouped: dict[UUID, list[BindingView]] = {item_id: [] for item_id in instance_ids}
        for row in rows:
            tenant = tenants.get(row.tenant_id)
            grouped.setdefault(row.product_instance_id, []).append(
                BindingView(
                    tenant_id=row.tenant_id,
                    tenant_slug=tenant.slug if tenant else "",
                    tenant_name=tenant.name if tenant else "",
                    product_instance_id=row.product_instance_id,
                    service_slug=row.service_slug,
                    status=row.status,
                )
            )
        return grouped

    def _resolve_location(
        self,
        *,
        environment: str,
        host: str,
        api_port: int | None,
        ui_host: str | None,
        ui_port: int | None,
        scheme: str,
        base_url: str,
        ui_url: str | None,
        notes: str,
    ) -> dict[str, Any]:
        env = (environment or "local_docker").strip().lower()
        if env not in ENVIRONMENTS:
            raise ValidationError(f"Unknown environment: {environment}")
        scheme = (scheme or "http").strip().lower()
        if scheme not in {"http", "https"}:
            raise ValidationError("scheme must be http or https")
        host = (host or "").strip()
        parsed_url = (base_url or "").strip().rstrip("/")
        if host and api_port is not None:
            api = build_url(scheme, host, int(api_port))
        elif parsed_url:
            scheme, host, api_port = parse_endpoint(parsed_url)
            api = parsed_url
        else:
            raise ValidationError("Provide host + API port, or a full API URL")
        ui = (ui_url or "").strip().rstrip("/") or None
        resolved_ui_host = (ui_host or "").strip() or None
        resolved_ui_port = ui_port
        if ui and not resolved_ui_host:
            _, resolved_ui_host, parsed_ui_port = parse_endpoint(ui)
            if resolved_ui_port is None:
                resolved_ui_port = parsed_ui_port
        elif resolved_ui_host and resolved_ui_port is not None and not ui:
            ui = build_url(scheme, resolved_ui_host, int(resolved_ui_port))
        return {
            "environment": env,
            "host": host,
            "api_port": int(api_port) if api_port is not None else None,
            "ui_host": resolved_ui_host,
            "ui_port": int(resolved_ui_port) if resolved_ui_port is not None else None,
            "scheme": scheme,
            "base_url": api,
            "ui_url": ui,
            "notes": (notes or "").strip()[:500],
        }

    def _to_view(
        self,
        row: ProductInstanceModel,
        bindings: list[BindingView] | None = None,
    ) -> ProductInstanceView:
        if row.base_url:
            scheme, host, api_port = parse_endpoint(row.base_url)
        else:
            scheme, host, api_port = "http", "", None
        host = row.host or host
        api_port = row.api_port if row.api_port is not None else api_port
        ui_host = row.ui_host
        ui_port = row.ui_port
        if row.ui_url and not ui_host:
            _, ui_host, ui_port = parse_endpoint(row.ui_url)
        return ProductInstanceView(
            id=row.id,
            slug=row.slug,
            name=row.name,
            base_url=row.base_url,
            ui_url=row.ui_url,
            status=row.status,
            version=row.version,
            client_id=row.client_id,
            last_heartbeat_at=row.last_heartbeat_at,
            environment=row.environment or "local_docker",
            host=host,
            api_port=api_port,
            ui_host=ui_host,
            ui_port=ui_port,
            scheme=row.scheme or scheme,
            notes=row.notes or "",
            bindings=bindings or [],
        )


class HubGatewayService:
    """Service-to-service surface consumed by HubPlatformAdapter."""

    def __init__(
        self,
        *,
        settings: Settings,
        password_hasher: PasswordHasher,
        query_bus: QueryBus,
        authorization: AuthorizationService,
        catalog: ServiceCatalogService,
        audit: AuditService,
    ) -> None:
        self._settings = settings
        self._hasher = password_hasher
        self._query_bus = query_bus
        self._authorization = authorization
        self._catalog = catalog
        self._audit = audit

    async def issue_token(self, client_id: str, client_secret: str) -> dict[str, Any]:
        session = get_current_session()
        result = await session.execute(
            select(ProductInstanceModel).where(ProductInstanceModel.client_id == client_id)
        )
        row = result.scalar_one_or_none()
        if row is None or row.status == "disabled":
            raise UnauthorizedError("Invalid product credentials")
        if not self._hasher.verify(
            PlainPassword.from_login_attempt(client_secret),
            HashedPassword.from_primitive(row.client_secret_hash),
        ):
            raise UnauthorizedError("Invalid product credentials")
        now = datetime.now(UTC)
        payload = {
            "sub": str(row.id),
            "client_id": row.client_id,
            "slug": row.slug,
            "token_use": "service",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=_SERVICE_TOKEN_MINUTES)).timestamp()),
        }
        token = jwt.encode(
            payload,
            self._settings.jwt_secret_key,
            algorithm=self._settings.jwt_algorithm,
        )
        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": _SERVICE_TOKEN_MINUTES * 60,
        }

    def decode_service_token(self, token: str) -> dict[str, Any]:
        try:
            payload = jwt.decode(
                token,
                self._settings.jwt_secret_key,
                algorithms=[self._settings.jwt_algorithm],
            )
        except jwt.InvalidTokenError as exc:
            raise UnauthorizedError("Invalid service token") from exc
        if payload.get("token_use") != "service":
            raise UnauthorizedError("Invalid service token")
        return payload

    async def heartbeat(self, instance_id: UUID, version: str, status: str) -> None:
        row = await get_current_session().get(ProductInstanceModel, instance_id)
        if row is None:
            raise NotFoundError("Product instance not found")
        row.version = version
        row.status = "online" if status == "ok" else status
        row.last_heartbeat_at = datetime.now(UTC)

    async def get_tenant(self, tenant_id: UUID) -> dict[str, Any]:
        row = await get_current_session().get(TenantModel, tenant_id)
        if row is None:
            raise NotFoundError("Tenant not found")
        return {"id": str(row.id), "slug": row.slug, "name": row.name, "is_active": row.is_active}

    async def introspect_user_token(self, token: str, token_service: Any) -> dict[str, Any]:
        claims = token_service.decode_access_token(token)
        user: UserDto = await self._query_bus.ask(GetUserByIdQuery(user_id=claims.user_id))
        access: EffectiveAccessDto = await self._query_bus.ask(
            ResolveEffectiveAccessQuery(role_ids=frozenset(user.role_ids))
        )
        tenant = await get_current_session().get(TenantModel, user.tenant_id)
        return {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "tenant_id": str(user.tenant_id),
            "tenant_slug": claims.tenant_slug,
            "tenant_name": tenant.name if tenant else "",
            "role_names": sorted(access.role_names),
            "permissions": sorted(access.permission_codes),
        }

    async def authorize(
        self,
        *,
        user_id: UUID,
        tenant_id: UUID,
        action: str,
    ) -> dict[str, Any]:
        user: UserDto = await self._query_bus.ask(GetUserByIdQuery(user_id=user_id))
        if user.tenant_id != tenant_id:
            return {"allowed": False, "reason": "tenant_mismatch"}
        service = action.split(".", 1)[0]
        if service in _PRODUCT_SLUGS:
            namespaces = await self._catalog.entitled_namespaces(tenant_id)
            allowed = service in namespaces
            return {
                "allowed": allowed,
                "reason": "entitlement" if allowed else "not_entitled",
            }
        access: EffectiveAccessDto = await self._query_bus.ask(
            ResolveEffectiveAccessQuery(role_ids=frozenset(user.role_ids))
        )
        principal = CurrentUser(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            tenant_id=user.tenant_id,
            tenant_slug="",
            role_ids=user.role_ids,
            role_names=access.role_names,
            permissions=access.permission_codes,
        )
        tokens = bind_tenant(tenant_id)
        try:
            decision = await self._authorization.check(
                user=principal,
                action=action,
                context=RequestContext(),
            )
        finally:
            unbind_tenant(*tokens)
        return {"allowed": decision.allowed, "reason": decision.reason}

    async def check_entitlement(self, tenant_id: UUID, capability: str) -> dict[str, bool]:
        namespaces = await self._catalog.entitled_namespaces(tenant_id)
        if capability in namespaces:
            return {"entitled": True}
        mapping = {
            "BASIC_TRACKING": "tracking",
            "ADVANCED_TELEMETRY": "tracking",
            "IOT_CORE": "iot",
            "SNMP_POLLING": "snmp",
            "GIS_CORE": "gis",
        }
        service = mapping.get(capability, capability)
        return {"entitled": service in namespaces}

    async def write_audit(self, body: dict[str, Any]) -> None:
        tenant_id = UUID(body["tenant_id"]) if body.get("tenant_id") else None
        if tenant_id is None:
            return
        await self._audit.persist(
            action=str(body.get("action") or "product.event"),
            actor_user_id=UUID(body["user_id"]) if body.get("user_id") else None,
            actor_type="product",
            resource_type=body.get("resource_type"),
            resource_id=str(body["resource_id"]) if body.get("resource_id") else None,
            payload=body.get("metadata") or {},
            tenant_id=tenant_id,
        )
