# Сущности для контрагента

from enum import StrEnum
from uuid import UUID

from pydantic import EmailStr, Field

from .base import Entity


class CounterpartyType(StrEnum):
    """Типы Контрагентов"""

    INDIVIDUAL = "Физическое лицо"
    INDIVIDUAL_ENTREPRENEUR = "Индивидуальный предприниматель"
    LEGAL_ENTITY = "Юридическое лицо"
    FOREIGN_LEGAL_ENTITY = "Иностранное юридическое лицо"
    BRANCH = "Обособленное подразделение"


class Counterparty(Entity):
    """Контрагент - компания или физ.лицо"""

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
        pattern=r"^\d{8,10}$"
    )
    phone: str = Field(..., title="Номер телефона", max_length=20)
    email: EmailStr = Field(..., title="Основной email")
    address: str | None = Field(default=None, title="Адрес")
    avatar_url: str | None = Field(None, description="URL адрес аватарки")
    is_active: bool = Field(default=True, description="Активен ли контрагент")


class ContactPerson(Entity):
    """Контактное лицо контрагента (физическое лицо)"""

    counterparty_id: UUID = Field(..., description="Ссылка на контрагента")

    first_name: str | None = Field(default=None, title="Имя")
    last_name: str | None = Field(default=None, title="Фамилия")
    middle_name: str | None = Field(default=None, title="Отчество")
    phone: str = Field(..., title="Номер телефона")
    email: EmailStr = Field(..., title="Email")
    messengers: dict[str, str] = Field(
        default_factory=dict,
        description="Другие мессенджеры",
        examples=[{"telegram": "@tg_user_123", "vk": "@vk_user_123"}]
    )

    @property
    def full_name(self) -> str:
        """ФИО контактного лица"""

        return " ".join(filter(None, [self.last_name, self.first_name, self.middle_name]))
