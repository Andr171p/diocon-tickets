from typing import Self

import secrets
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from uuid import UUID

from src.shared.domain.entities import Entity
from src.shared.domain.exceptions import InvariantViolationError
from src.shared.utils.time import current_datetime, get_expiration_time

from .events import UserInvited
from .vo import Email, FullName, PasswordHash, Username, UserRole

INVITATION_EXPIRES_IN_DAYS = 7


def _validate_roles_consistency(roles: set[UserRole]) -> None:
    """
    Проверяет, что набор ролей не содержит одновременно клиентские и сотруднические роли.
    """

    customer_roles = roles & UserRole.customer_roles()
    staff_roles = roles & UserRole.staff_roles()

    if customer_roles and staff_roles:
        raise InvariantViolationError("User cannot be both customer and staff")


def _validate_counterparty(roles: set[UserRole], counterparty_id: UUID | None = None) -> None:
    """
    Проверяет согласованность набора ролей и контрагента.
    Рекомендуется вызывать после `_validate_roles_consistency`.
    """

    customer_roles = roles & UserRole.customer_roles()
    staff_roles = roles & UserRole.staff_roles()

    if customer_roles and counterparty_id is None:
        raise InvariantViolationError("Counterparty must be specified for clients")

    if staff_roles and counterparty_id is not None:
        raise InvariantViolationError("Staff users should not have direct counterparty")


def _generate_invite_token(length: int = 32) -> str:
    """
    Генерирует токен для активации приглашения.
    """

    return secrets.token_urlsafe(length)


@dataclass(kw_only=True)
class User(Entity):
    """
    Пользователь системы (человек).
    """

    email: Email
    username: Username | None = None
    full_name: FullName | None = None
    avatar_url: str | None = None
    roles: set[UserRole]
    counterparty_id: UUID | None = None
    password_hash: PasswordHash
    is_active: bool = True

    def __post_init__(self) -> None:

        _validate_roles_consistency(self.roles)

        _validate_counterparty(self.roles, self.counterparty_id)

    @property
    def is_staff(self) -> bool:
        return any(role.is_staff for role in self.roles)

    @property
    def is_customer(self) -> bool:
        return any(role.is_customer for role in self.roles)

    def has_role(self, role: UserRole) -> bool:
        return role in self.roles

    def has_any_role(self, roles: Iterable[UserRole]) -> bool:
        return bool(self.roles & set(roles))

    def has_all_roles(self, roles: Iterable[UserRole]) -> bool:
        return set(roles).issubset(self.roles)

    def grant_role(self, role: UserRole) -> None:
        if role in self.roles:
            return

        new_roles = self.roles | {role}
        _validate_roles_consistency(new_roles)
        _validate_counterparty(new_roles, self.counterparty_id)

        self.roles.add(role)
        self.updated_at = current_datetime()

    def revoke_role(self, role: UserRole) -> None:
        if len(self.roles) == 1:
            raise InvariantViolationError("User must have at least one role")

        if role not in self.roles:
            return

        new_roles = self.roles - {role}

        _validate_roles_consistency(new_roles)
        _validate_counterparty(new_roles, self.counterparty_id)

        self.roles.remove(role)
        self.updated_at = current_datetime()

    def replace_roles(self, new_roles: set[UserRole]) -> None:
        if not new_roles:
            raise InvariantViolationError("User must have at least one role")

        if new_roles == self.roles:
            return

        _validate_roles_consistency(new_roles)
        _validate_counterparty(new_roles, self.counterparty_id)

        self.roles = new_roles
        self.updated_at = current_datetime()


@dataclass(kw_only=True)
class Invitation(Entity):
    """
    Приглашение пользователя в систему.
    """

    email: Email
    token: str = field(default_factory=_generate_invite_token)
    invited_by: UUID
    granted_roles: set[UserRole]
    counterparty_id: UUID | None = None
    expires_at: datetime
    used_at: datetime | None = None
    is_used: bool = False

    def __post_init__(self) -> None:

        _validate_roles_consistency(self.granted_roles)

        _validate_counterparty(self.granted_roles, self.counterparty_id)

    @property
    def is_valid(self) -> bool:
        return not self.is_used and self.expires_at > current_datetime()

    @classmethod
    def create(
            cls,
            email: Email,
            invited_by: UUID,
            granted_roles: set[UserRole],
            counterparty_id: UUID | None = None,
    ) -> Self:
        expires_at = get_expiration_time(expires_in=timedelta(days=INVITATION_EXPIRES_IN_DAYS))
        invitation = cls(
            email=email,
            invited_by=invited_by,
            granted_roles=granted_roles,
            counterparty_id=counterparty_id,
            expires_at=expires_at,
        )
        invitation.invite()
        return invitation

    def invite(self) -> None:
        self.register_event(
            UserInvited(
                invitation_id=self.id,
                email=self.email,
                granted_roles=self.granted_roles,
                counterparty_id=self.counterparty_id,
                invited_by=self.invited_by,
            )
        )

    def mark_as_used(self) -> None:
        self.used_at = current_datetime()
        self.is_used = True
