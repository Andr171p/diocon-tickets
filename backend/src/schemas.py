from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, PositiveInt

from .core.entities import CounterpartyType, UserRole


class CounterpartyCreate(BaseModel):
    """Создание контрагента"""

    model_config = ConfigDict(from_attributes=True)

    counterparty_type: CounterpartyType = Field(..., title="Тип контрагента")

    name: str = Field(..., title="Наименование", max_length=255)
    legal_name: str = Field(..., title="Юридическое наименование", max_length=255)
    inn: str | None = Field(default=None, title="ИНН", max_length=12)
    kpp: str = Field(..., title="КПП", max_length=9)
    okpo: str | None = Field(
        default=None,
        title="ОКПО",
        description="Код по Общероссийскому классификатору предприятий и организаций",
        max_length=10,
        pattern=r"^\d{8,10}$",
    )
    phone: str = Field(..., title="Номер телефона", max_length=20)
    email: EmailStr = Field(..., title="Основной email")
    address: str | None = Field(default=None, title="Адрес")


class CounterpartyUpdate(BaseModel):
    """Обновление контрагента"""

    counterparty_type: CounterpartyType | None = Field(None, title="Тип контрагента")

    name: str | None = Field(None, title="Наименование", max_length=255)
    legal_name: str | None = Field(None, title="Юридическое наименование", max_length=255)
    inn: str | None = Field(None, title="ИНН", max_length=12)
    kpp: str | None = Field(None, title="КПП", max_length=9)
    okpo: str | None = Field(
        default=None,
        title="ОКПО",
        description="Код по Общероссийскому классификатору предприятий и организаций",
        max_length=10,
        pattern=r"^\d{8,10}$",
    )
    phone: str | None = Field(None, title="Номер телефона", max_length=20)
    email: EmailStr | None = Field(None, title="Основной email")
    address: str | None = Field(None, title="Адрес")


class ContactPersonAdd(BaseModel):
    """Добавление контактного лица"""

    first_name: str | None = Field(default=None, title="Имя")
    last_name: str | None = Field(default=None, title="Фамилия")
    middle_name: str | None = Field(default=None, title="Отчество")
    phone: str = Field(..., title="Номер телефона")
    email: EmailStr = Field(..., title="Email")
    messengers: dict[str, str] = Field(
        default_factory=dict,
        description="Другие мессенджеры",
        examples=[{"telegram": "tg_user_123", "vk": "vk_user_123"}],
    )


class ContactPersonUpdate(BaseModel):
    """Обновление контактного лица"""

    first_name: str | None = Field(None, title="Имя")
    last_name: str | None = Field(None, title="Фамилия")
    middle_name: str | None = Field(None, title="Отчество")
    phone: str | None = Field(None, title="Номер телефона")
    email: EmailStr | None = Field(None, title="Email")
    messengers: dict[str, str] | None = Field(
        default=None,
        description="Другие мессенджеры",
        examples=[{"telegram": "tg_user_123", "vk": "vk_user_123"}],
    )


class InvitationCreate(BaseModel):
    """Отправка приглашения"""

    email: EmailStr = Field(..., description="Email пользователя")
    role: UserRole = Field(
        ..., description="Роль, которая будет установлена пользователю"
    )
    counterparty_id: UUID | None = Field(None, description="Для клиентов - ID контрагента")


class InvitationResponse(BaseModel):
    """Схема ответа отправленного приглашения"""

    model_config = ConfigDict(from_attributes=True)

    email: EmailStr
    created_by: UUID
    intended_role: UserRole
    counterparty_id: UUID | None = None
    expires_at: datetime
    is_used: bool


class TokenType(StrEnum):
    """Типы токенов"""

    ACCESS = "access"
    REFRESH = "refresh"


class Token(BaseModel):
    """Схема 'access' токена"""

    access_token: str
    token_type: str = Field("Bearer", frozen=True)
    expires_at: PositiveInt = Field(..., description="Время истечения токена в формате timestamp")


class TokensPair(BaseModel):
    """Пара токенов 'access' и 'refresh'"""

    access_token: str
    refresh_token: str
    token_type: str = Field(default="Bearer", frozen=True)
    expires_at: PositiveInt = Field(
        ..., description="Время истечения access токена в формате timestamp"
    )


class UserCreateForm(BaseModel):
    """Форма для создания пользователя"""

    username: str | None = Field(
        None, description="Никнейм пользователя", examples=["ivan_ivanov"]
    )
    full_name: str | None = Field(
        None, max_length=150, description="ФИО", examples=["Иванов Иван Иванович"]
    )
    password: str = Field(..., description="Пароль, который придумал пользователь")


class UserResponse(BaseModel):
    """Модель для API ответа с данными о пользователе"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    username: str | None = None
    full_name: str | None = None
    avatar_url: str | None = None
    role: UserRole
    counterparty_id: UUID | None = None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime
