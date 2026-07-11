from typing import Annotated

from datetime import datetime
from uuid import UUID

from fastapi import Body
from pydantic import BaseModel, EmailStr, Field, PositiveInt

from .domain.vo import UserRole, UserType

RefreshToken = Annotated[
    str, Body(..., embed=True, description="Refresh токен для получения новой пары JWT")
]


class Tokens(BaseModel):
    """
    Пара токенов access и refresh.
    """

    access_token: str = Field(..., description="Access токен")
    refresh_token: str = Field(..., description="Refresh токен")
    token_type: str = Field(default="Bearer", frozen=True)
    expires_at: PositiveInt = Field(
        ..., description="Время истечения access токена в формате timestamp"
    )


class UserCreate(BaseModel):
    """
    Форма для создания/регистрации пользователя.
    """

    username: str | None = Field(
        None, description="Никнейм пользователя", examples=["i.i.ivanov"]
    )
    full_name: str | None = Field(
        None, max_length=150, description="ФИО", examples=["Иванов Иван Иванович"]
    )
    password: str = Field(
        ..., min_length=6, max_length=30, description="Пароль, который придумал пользователь"
    )


class UserResponse(BaseModel):
    """
    Полная информация о пользователе.
    """

    id: UUID = Field(..., description="Уникальный идентификатор пользователя")
    created_at: datetime = Field(..., description="Дата регистрации")
    updated_at: datetime = Field(..., description="Дата обновления")

    email: EmailStr = Field(..., description="Email адрес (уникальный)")
    username: str | None = Field(None, description="Никнейм пользователя")
    full_name: str | None = Field(None, description="ФИО")
    avatar_url: str | None = Field(None, description="URL адрес изображения")

    roles: set[UserRole] = Field(
        ..., description="Назначенные роли", examples=[{"support_agent", "developer"}]
    )
    counterparty_id: UUID | None = Field(
        None, description="Контрагент к которому относится пользователь"
    )
    is_active: bool = Field(True, description="Активен ли пользователь")


class LogoutRequest(BaseModel):
    refresh_token: str | None = Field(None, description="refresh токен пользователя (опционален)")


class CurrentUser(BaseModel):
    """
    Текущий пользователь, который делает запрос.
    """

    id: UUID = Field(..., description="Уникальный ID пользователя")
    email: EmailStr = Field(..., description="Email адрес учётной записи")
    roles: list[UserRole] = Field(..., description="Список назначенных ролей")
    counterparty_id: UUID | None = Field(None, description="ID контрагента (для клиентов)")


class UserReference(BaseModel):
    """Ссылка на пользователя."""

    id: UUID = Field(description="Идентификатор пользователя")
    full_name: str = Field(description="ФИО пользователя", examples=["Иванов Иван Иванович"])
    email: EmailStr = Field(description="Логин пользователя")
    type: UserType = Field(description="Сотрудник или внешний клиент")


class InvitationBase(BaseModel):
    email: EmailStr = Field(..., description="Email пользователя")
    granted_roles: set[UserRole] = Field(
        ..., description="Роли, которые будут назначены пользователю после принятия приглашения"
    )
    counterparty_id: UUID | None = Field(
        None, description="Для клиентов необходимо указать контрагента"
    )


class InvitationCreate(InvitationBase):
    """
    Создать приглашение для пользователя.
    """


class InvitationResponse(InvitationBase):
    """
    Полная информация о приглашении.
    """

    id: UUID = Field(..., description="Уникальный ID приглашения")
    created_at: datetime = Field(..., description="Дата создания")

    invited_by: UUID = Field(..., description="Тот, кто создал приглашение")
    expires_at: datetime = Field(..., description="Дата истечения срока")
    used_at: datetime | None = Field(None, description="Дата, когда использовали приглашение")
    is_used: bool = Field(..., description="Использовано ли приглашение")
