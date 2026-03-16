from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import EmailStr, Field, SecretStr

from ...utils.commons import current_datetime
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
    password_hash: str = Field(..., description="Хеш пароля")
    is_active: bool = Field(True, description="Активен ли пользователь")


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
