from typing import Self

import secrets
from datetime import datetime
from uuid import UUID

from pydantic import EmailStr, Field, model_validator

from ...utils.commons import current_datetime
from .base import Entity
from .user import UserRole


def generate_invite_token(length: int = 32) -> str:
    """Генерация токена для активации приглашения"""

    return secrets.token_urlsafe(length)


class Invitation(Entity):
    """Приглашение пользователя в тикет-систему"""

    email: EmailStr = Field(..., description="Email пользователя")
    token: str = Field(
        default_factory=generate_invite_token,
        description="Уникальный токен для ссылки-приглашения"
    )
    created_by: UUID = Field(..., description="Отправитель приглашения")
    intended_role: UserRole = Field(
        ..., description="Роль, которая будет установлена пользователю"
    )
    counterparty_id: UUID | None = Field(None, description="Для клиентов - ID контрагента")
    expires_at: datetime = Field(..., description="Время истечения приглашения")
    is_used: bool = Field(False, description="Использовано ли приглашение")

    @model_validator(mode="after")
    def validate_rules(self) -> Self:
        """Проверка необходимых правил"""

        if self.intended_role in {UserRole.CUSTOMER, UserRole.CUSTOMER_ADMIN} \
                and self.counterparty_id is None:
            raise ValueError("For invitations to clients, you must specify a counterparty ID!")
        if self.intended_role in {UserRole.SUPPORT_AGENT, UserRole.SUPPORT_MANAGER} \
                and self.counterparty_id is not None:
            raise ValueError(
                "For internal employees, counterparty ID does not need to be specified!"
            )
        return self

    @property
    def is_valid(self) -> bool:
        """Актуально ли приглашение"""

        return not self.is_used and self.expires_at > current_datetime()

    def mark_as_used(self) -> None:
        """Пометить, как использованное"""

        self.is_used = True
