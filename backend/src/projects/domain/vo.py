from typing import ClassVar, Self

import re
from dataclasses import dataclass
from enum import StrEnum, auto

from src.shared.domain.vo import ValueObject


class ProjectStatus(StrEnum):
    """Статус проекта"""

    ACTIVE = auto()
    ON_HOLD = auto()  # На удержании
    ARCHIVED = auto()
    COMPLETED = auto()


class ProjectStageStatus(StrEnum):
    """Статус этапа проекта"""

    PLANNED = auto()
    ACTIVE = auto()
    COMPLETED = auto()
    ON_HOLD = auto()  # Приостановлен
    SKIPPED = auto()  # Пропущен


class MemberRole(StrEnum):
    """
    Роли участника проекта.
    """

    OWNER = auto()
    MANAGER = auto()  # Может управлять участниками, настройками
    CONTRIBUTOR = auto()  # Обычный участник (агент, разработчик)
    VIEWER = auto()  # только просмотр (аудитор)
    CUSTOMER = auto()  # клиент (принадлежит контрагенту)
    CUSTOMER_MANAGER = auto()  # расширенные права (менеджер со стороны клиента)

    @property
    def is_staff(self) -> bool:
        return self in {self.CONTRIBUTOR, self.MANAGER, self.OWNER}

    @property
    def is_customer(self) -> bool:
        return self in {self.CUSTOMER, self.CUSTOMER_MANAGER}

    @classmethod
    def staff_roles(cls) -> set[Self]:
        """
        Набор ролей для внутренних сотрудников.
        """

        return {cls.CONTRIBUTOR, cls.MANAGER, cls.OWNER}

    @classmethod
    def customer_roles(cls) -> set[Self]:
        """
        Набор ролей для внешних клиентов.
        """

        return {cls.VIEWER, cls.CUSTOMER, cls.CUSTOMER_MANAGER}


@dataclass(frozen=True)
class ProjectKey(ValueObject):
    """
    Уникальный ключ проекта.

    Формат:
     - Длина от 2 до 10 символов
     - Только заглавные латинские буквы (A-Z) и цифры (0-9)
     - Первый символ — обязательно буква
     - Без пробелов, дефисов, подчёркиваний и других разделителей

    Примеры: "PRJ", "MOB_APP", "BACKEND1", "PROEKT"
    """

    PATTERN: ClassVar[re.Pattern] = re.compile(r"^[A-Z][A-Z0-9]{1,9}$")

    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("Project key cannot be empty")

        cleaned = re.sub(r"[^A-Za-z0-9]", "", self.value.upper().strip())
        if not self.PATTERN.match(cleaned):
            raise ValueError(
                f"Invalid project key format: '{self.value}'. "
                "Key must be 2-10 characters long, planned_start with a letter (A-Z), "
                "and contain only letters and digits (no spaces, underscores, or Cyrillic)."
            )

        object.__setattr__(self, "value", cleaned)

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"ProjectKey('{self.value}')"
