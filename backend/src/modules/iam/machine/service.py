"""Service accounts and API keys."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select

from src.modules.iam.models import ApiKeyModel, ServiceAccountModel
from src.modules.iam.utils import generate_api_key_raw
from src.shared.infrastructure.exceptions import NotFoundError, UnauthorizedError
from src.shared.infrastructure.session_context import get_current_session
from src.shared.infrastructure.tenant_context import require_current_tenant_id


class MachineIdentityService:
    async def create_service_account(
        self, *, name: str, description: str = "", role_ids: list[UUID] | None = None
    ) -> ServiceAccountModel:
        model = ServiceAccountModel(
            id=uuid4(),
            tenant_id=require_current_tenant_id(),
            name=name,
            description=description,
            role_ids=role_ids or [],
        )
        db = get_current_session()
        db.add(model)
        await db.flush()
        return model

    async def list_service_accounts(self) -> list[ServiceAccountModel]:
        db = get_current_session()
        result = await db.execute(
            select(ServiceAccountModel).where(
                ServiceAccountModel.tenant_id == require_current_tenant_id()
            )
        )
        return list(result.scalars().all())

    async def get_service_account(self, account_id: UUID) -> ServiceAccountModel:
        db = get_current_session()
        model = await db.get(ServiceAccountModel, account_id)
        if model is None or model.tenant_id != require_current_tenant_id():
            raise NotFoundError("Service account not found")
        return model

    async def update_service_account(
        self,
        account_id: UUID,
        *,
        name: str | None = None,
        description: str | None = None,
        role_ids: list[UUID] | None = None,
        is_active: bool | None = None,
    ) -> ServiceAccountModel:
        model = await self.get_service_account(account_id)
        if name is not None:
            model.name = name
        if description is not None:
            model.description = description
        if role_ids is not None:
            model.role_ids = role_ids
        if is_active is not None:
            model.is_active = is_active
        await get_current_session().flush()
        return model

    async def delete_service_account(self, account_id: UUID) -> None:
        model = await self.get_service_account(account_id)
        await get_current_session().delete(model)

    async def create_api_key(
        self,
        *,
        service_account_id: UUID,
        name: str,
        scopes: list[str] | None = None,
        expires_at: datetime | None = None,
    ) -> tuple[ApiKeyModel, str]:
        await self.get_service_account(service_account_id)
        prefix, raw, key_hash = generate_api_key_raw()
        model = ApiKeyModel(
            id=uuid4(),
            tenant_id=require_current_tenant_id(),
            service_account_id=service_account_id,
            name=name,
            prefix=prefix,
            key_hash=key_hash,
            scopes=scopes or [],
            expires_at=expires_at,
        )
        db = get_current_session()
        db.add(model)
        await db.flush()
        return model, raw

    async def list_api_keys(self, service_account_id: UUID | None = None) -> list[ApiKeyModel]:
        db = get_current_session()
        stmt = select(ApiKeyModel).where(ApiKeyModel.tenant_id == require_current_tenant_id())
        if service_account_id is not None:
            stmt = stmt.where(ApiKeyModel.service_account_id == service_account_id)
        result = await db.execute(stmt.order_by(ApiKeyModel.created_at.desc()))
        return list(result.scalars().all())

    async def revoke_api_key(self, key_id: UUID) -> None:
        db = get_current_session()
        model = await db.get(ApiKeyModel, key_id)
        if model is None or model.tenant_id != require_current_tenant_id():
            raise NotFoundError("API key not found")
        model.revoked_at = datetime.now(UTC)
        await db.flush()

    async def authenticate_api_key(self, raw_key: str) -> ApiKeyModel:
        from src.modules.iam.utils import sha256_hex

        db = get_current_session()
        result = await db.execute(
            select(ApiKeyModel).where(
                ApiKeyModel.key_hash == sha256_hex(raw_key),
                ApiKeyModel.tenant_id == require_current_tenant_id(),
            )
        )
        key = result.scalar_one_or_none()
        if key is None or key.revoked_at is not None:
            raise UnauthorizedError("Invalid API key")
        if key.expires_at and key.expires_at < datetime.now(UTC):
            raise UnauthorizedError("API key expired")
        account = await self.get_service_account(key.service_account_id)
        if not account.is_active:
            raise UnauthorizedError("Service account inactive")
        key.last_used_at = datetime.now(UTC)
        await db.flush()
        return key
