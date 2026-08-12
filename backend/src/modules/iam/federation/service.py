"""Federation / SSO identity providers."""

from __future__ import annotations

import base64
from typing import Any
from urllib.parse import urlencode
from uuid import UUID, uuid4

from sqlalchemy import select

from src.modules.iam.models import FederatedIdentityModel, IdentityProviderModel
from src.modules.iam.utils import generate_token
from src.modules.users.commands.user_commands import CreateUserCommand
from src.modules.users.queries.user_queries import GetUserByEmailQuery
from src.shared.application.command_bus import CommandBus
from src.shared.application.query_bus import QueryBus
from src.shared.infrastructure.exceptions import NotFoundError, ValidationError
from src.shared.infrastructure.session_context import get_current_session
from src.shared.infrastructure.tenant_context import require_current_tenant_id


class FederationService:
    def __init__(self, command_bus: CommandBus, query_bus: QueryBus) -> None:
        self._commands = command_bus
        self._queries = query_bus

    async def create_provider(
        self,
        *,
        name: str,
        provider_type: str,
        client_id: str | None = None,
        client_secret: str | None = None,
        issuer: str | None = None,
        metadata_url: str | None = None,
        attribute_mapping: dict[str, Any] | None = None,
    ) -> IdentityProviderModel:
        if provider_type not in {"oidc", "saml"}:
            raise ValidationError("provider_type must be oidc or saml")
        model = IdentityProviderModel(
            id=uuid4(),
            tenant_id=require_current_tenant_id(),
            name=name,
            provider_type=provider_type,
            client_id=client_id,
            client_secret_encrypted=client_secret,
            issuer=issuer,
            metadata_url=metadata_url,
            attribute_mapping=attribute_mapping or {"email": "email", "sub": "sub"},
            enabled=True,
        )
        db = get_current_session()
        db.add(model)
        await db.flush()
        return model

    async def list_providers(self, *, enabled_only: bool = False) -> list[IdentityProviderModel]:
        db = get_current_session()
        stmt = select(IdentityProviderModel).where(
            IdentityProviderModel.tenant_id == require_current_tenant_id()
        )
        if enabled_only:
            stmt = stmt.where(IdentityProviderModel.enabled.is_(True))
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_provider(self, provider_id: UUID) -> IdentityProviderModel:
        db = get_current_session()
        model = await db.get(IdentityProviderModel, provider_id)
        if model is None or model.tenant_id != require_current_tenant_id():
            raise NotFoundError("Identity provider not found")
        return model

    async def update_provider(self, provider_id: UUID, **fields: Any) -> IdentityProviderModel:
        model = await self.get_provider(provider_id)
        for key, value in fields.items():
            if value is not None and hasattr(model, key):
                setattr(model, key, value)
        await get_current_session().flush()
        return model

    async def delete_provider(self, provider_id: UUID) -> None:
        model = await self.get_provider(provider_id)
        await get_current_session().delete(model)

    def build_oidc_authorize_url(
        self, provider: IdentityProviderModel, *, redirect_uri: str, state: str
    ) -> str:
        if not provider.issuer or not provider.client_id:
            raise ValidationError("OIDC provider incomplete")
        authorize = provider.metadata_url or f"{provider.issuer.rstrip('/')}/authorize"
        if authorize.endswith("/.well-known/openid-configuration"):
            authorize = provider.issuer.rstrip("/") + "/authorize"
        query = urlencode(
            {
                "client_id": provider.client_id,
                "response_type": "code",
                "scope": "openid email profile",
                "redirect_uri": redirect_uri,
                "state": state,
            }
        )
        return f"{authorize}?{query}"

    async def link_or_provision(
        self,
        *,
        provider_id: UUID,
        external_subject: str,
        email: str,
        full_name: str,
        jit: bool = False,
    ) -> UUID:
        db = get_current_session()
        tenant_id = require_current_tenant_id()
        existing = await db.execute(
            select(FederatedIdentityModel).where(
                FederatedIdentityModel.tenant_id == tenant_id,
                FederatedIdentityModel.provider_id == provider_id,
                FederatedIdentityModel.external_subject == external_subject,
            )
        )
        link = existing.scalar_one_or_none()
        if link is not None:
            return link.user_id
        try:
            user = await self._queries.ask(
                GetUserByEmailQuery(tenant_id=tenant_id, email=email)
            )
            user_id = user.id
        except Exception:
            if not jit:
                raise ValidationError("No local user linked for federated identity")
            username = email.split("@")[0][:32]
            user_id = await self._commands.execute(
                CreateUserCommand(
                    tenant_id=tenant_id,
                    email=email,
                    username=username,
                    full_name=full_name or username,
                    password=generate_token(24) + "A1!",
                )
            )
        db.add(
            FederatedIdentityModel(
                id=uuid4(),
                tenant_id=tenant_id,
                user_id=user_id,
                provider_id=provider_id,
                external_subject=external_subject,
            )
        )
        await db.flush()
        return user_id

    def parse_saml_response_stub(self, saml_response_b64: str) -> dict[str, str]:
        """Development helper: decode base64 payload as email=...&name_id=..."""
        try:
            raw = base64.b64decode(saml_response_b64).decode("utf-8")
        except Exception as exc:
            raise ValidationError("Invalid SAMLResponse") from exc
        data: dict[str, str] = {}
        for part in raw.split("&"):
            if "=" in part:
                k, v = part.split("=", 1)
                data[k] = v
        if "name_id" not in data and "email" not in data:
            raise ValidationError("SAMLResponse missing name_id/email")
        return data
