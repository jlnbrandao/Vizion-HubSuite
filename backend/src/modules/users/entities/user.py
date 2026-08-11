"""User Aggregate Root — owns User ⇄ Role association via role IDs.

Does NOT import Role entities. Cross-module validation via QueryBus
(CheckRolesExistQuery). Password is always stored as HashedPassword.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from src.modules.users.events.user_events import (
    RolesAssignedToUserEvent,
    RolesRevokedFromUserEvent,
    UserCreatedEvent,
    UserDeletedEvent,
    UserPasswordChangedEvent,
    UserUpdatedEvent,
)
from src.modules.users.value_objects.email import Email
from src.modules.users.value_objects.full_name import FullName
from src.modules.users.value_objects.hashed_password import HashedPassword
from src.modules.users.value_objects.username import Username
from src.shared.domain.aggregate_root import AggregateRoot


@dataclass(eq=False, kw_only=True)
class User(AggregateRoot):
    tenant_id: UUID
    email: Email
    username: Username
    full_name: FullName
    hashed_password: HashedPassword
    role_ids: set[UUID] = field(default_factory=set)
    is_active: bool = True
    credentials_version: int = 0

    @classmethod
    def create(
        cls,
        *,
        tenant_id: UUID,
        email: Email,
        username: Username,
        full_name: FullName,
        hashed_password: HashedPassword,
    ) -> User:
        user = cls(
            tenant_id=tenant_id,
            email=email,
            username=username,
            full_name=full_name,
            hashed_password=hashed_password,
            credentials_version=0,
        )
        user.raise_event(UserCreatedEvent(aggregate_id=user.id, email=email.value))
        return user

    def change_email(self, email: Email) -> None:
        if self.email == email:
            return
        self.email = email
        self.touch()
        self.raise_event(UserUpdatedEvent(aggregate_id=self.id, email=email.value))

    def change_username(self, username: Username) -> None:
        if self.username == username:
            return
        self.username = username
        self.touch()
        self.raise_event(UserUpdatedEvent(aggregate_id=self.id, email=self.email.value))

    def change_full_name(self, full_name: FullName) -> None:
        if self.full_name == full_name:
            return
        self.full_name = full_name
        self.touch()
        self.raise_event(UserUpdatedEvent(aggregate_id=self.id, email=self.email.value))

    def change_password(self, hashed_password: HashedPassword) -> None:
        self.hashed_password = hashed_password
        self.bump_credentials_version()
        self.raise_event(
            UserPasswordChangedEvent(aggregate_id=self.id, email=self.email.value)
        )

    def bump_credentials_version(self) -> None:
        self.credentials_version += 1
        self.touch()

    def assign_roles(self, role_ids: set[UUID]) -> None:
        new_ids = role_ids - self.role_ids
        if not new_ids:
            return
        self.role_ids |= new_ids
        self.bump_credentials_version()
        self.raise_event(
            RolesAssignedToUserEvent(
                aggregate_id=self.id,
                email=self.email.value,
                role_ids=tuple(sorted(new_ids, key=str)),
            )
        )

    def revoke_roles(self, role_ids: set[UUID]) -> None:
        removed = role_ids & self.role_ids
        if not removed:
            return
        self.role_ids -= removed
        self.bump_credentials_version()
        self.raise_event(
            RolesRevokedFromUserEvent(
                aggregate_id=self.id,
                email=self.email.value,
                role_ids=tuple(sorted(removed, key=str)),
            )
        )

    def replace_roles(self, role_ids: set[UUID]) -> None:
        to_add = role_ids - self.role_ids
        to_remove = self.role_ids - role_ids
        if to_add:
            self.assign_roles(to_add)
        if to_remove:
            self.revoke_roles(to_remove)

    def activate(self) -> None:
        if self.is_active:
            return
        self.is_active = True
        self.touch()
        self.raise_event(UserUpdatedEvent(aggregate_id=self.id, email=self.email.value))

    def deactivate(self) -> None:
        if not self.is_active:
            return
        self.is_active = False
        self.bump_credentials_version()
        self.raise_event(UserUpdatedEvent(aggregate_id=self.id, email=self.email.value))

    def mark_deleted(self) -> None:
        self.raise_event(UserDeletedEvent(aggregate_id=self.id, email=self.email.value))

    def has_role(self, role_id: UUID) -> bool:
        return role_id in self.role_ids
