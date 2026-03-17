from typing import Self

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import EmailStr, Field, model_validator

from ...utils.commons import current_datetime
from ..errors import InvariantViolationError
from .base import Entity


class UserRole(StrEnum):
    """Роли пользователей"""

    CUSTOMER_ADMIN = "customer_admin"  # администратор клиентской стороны
    CUSTOMER = "customer"  # клиент / обычный пользователь
    SUPPORT_AGENT = "support_agent"  # сотрудник поддержки
    SUPPORT_MANAGER = "support_manager"  # старший сотрудник поддержки
    ADMIN = "admin"  # системный администратор


class User(Entity):
    """Пользователь системы"""

    email: EmailStr = Field(..., description="Email пользователя")
    username: str | None = Field(
        None, description="Никнейм пользователя", examples=["IvanovIvanch"]
    )
    full_name: str | None = Field(
        None,
        max_length=150,
        description="ФИО",
        examples=["Иванов Иван Иванович"])
    avatar_url: str | None = Field(None, description="Аватарка пользователя")
    role: UserRole = Field(..., description="Роль пользователя", examples=[UserRole.CUSTOMER])
    counterparty_id: UUID | None = Field(
        None,
        description="""\
        Контрагент к которому принадлежит пользователь.
        Не нужно указывать для внутренних сотрудников.
        """
    )
    password_hash: str = Field(..., description="Хеш пароля")
    is_active: bool = Field(True, description="Активен ли пользователь")

    @model_validator(mode="after")
    def validate_rules(self) -> Self:
        """Проверка правил существования сущности"""

        if self.counterparty_id is None \
                and self.role in {UserRole.CUSTOMER, UserRole.CUSTOMER_ADMIN}:
            raise InvariantViolationError("Counterparty must be specified for clients")
        return self


class RefreshToken(Entity):
    """Схема 'refresh' токена - для ротации"""

    user_id: UUID = Field(..., description="ID пользователя, которому выдан токен")
    token: str = Field(..., description="Refresh токен")
    expires_at: datetime = Field(..., description="Дата истечения")
    revoked: bool = Field(False, description="Отозван ли токен")
    revoked_at: datetime | None = Field(None, description="Время отзыва")

    @property
    def is_valid(self) -> bool:
        """Проверка токена на валидность"""

        return not self.revoked and self.expires_at < current_datetime()
