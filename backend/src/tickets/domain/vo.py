from typing import ClassVar, Self

import re
from dataclasses import dataclass
from enum import StrEnum, auto

from src.projects.domain.vo import ProjectKey
from src.shared.domain.vo import ValueObject
from src.shared.utils.text import get_latin_slug


class TicketAction(StrEnum):
    """Действия меняющие состояние заявки."""

    EDIT = auto()
    ASSIGN = auto()
    START_PROGRESS = auto()
    PAUSE = auto()
    RESOLVE = auto()
    CLOSE = auto()
    REOPEN = auto()
    CANCEL = auto()
    APPROVE = auto()
    SUBMIT_FOR_APPROVAL = auto()
    REJECT = auto()


class TicketStatus(StrEnum):
    """Возможные статусы тикета"""

    # Начальные статусы
    NEW = auto()
    PENDING_APPROVAL = auto()

    # Рабочие статусы
    OPEN = auto()
    IN_PROGRESS = auto()
    WAITING = auto()
    PAUSED = auto()

    # Завершающие статусы
    RESOLVED = auto()
    CLOSED = auto()
    REOPENED = auto()

    # Дополнительные
    REJECTED = auto()
    CANCELED = auto()


class TicketType(StrEnum):
    """Тип заявки/тикета"""

    # Клиентские
    INCIDENT = "Инцидент"
    SERVICE_REQUEST = "Запрос на услугу"
    QUESTION = "Консультация"
    COMPLAINT = "Жалоба"

    # Внутренние
    TASK = "Задача"
    PROBLEM = "Проблема"
    CHANGE = "Запрос на изменение"
    IMPROVEMENT = "Улучшение"

    OTHER = "Прочее"


@dataclass(frozen=True)
class TicketPrefix(ValueObject):
    """
    Префикс для номера заявки.
    Префиксом может быть: ключ проекта, транслитерация наименования контрагента, ...

    Примеры:
     - INT
     - CRM
     - YANDEX
    """

    INTERNAL: ClassVar[str] = "INT"

    MIN_LENGTH: ClassVar[int] = 1
    MAX_LENGTH: ClassVar[int] = 10

    _PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"^[A-Z0-9]{1,10}$")

    value: str

    def __post_init__(self) -> None:
        if not self._PATTERN.fullmatch(self.value):
            raise ValueError(f"Invalid ticket prefix: {self.value}")

    @classmethod
    def internal(cls) -> Self:
        return cls(cls.INTERNAL)

    @classmethod
    def from_project(cls, key: ProjectKey) -> Self:
        return cls(key.value)

    @classmethod
    def from_counterparty(cls, name: str) -> Self:
        slug = get_latin_slug(name, upper=True)
        return cls(slug[:cls.MAX_LENGTH])

    @property
    def is_internal(self) -> bool:
        return self.value == self.INTERNAL

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class TicketNumber(ValueObject):
    """Уникальный номер заявки в формате - PREFIX-YY-NNNNNNNN."""

    YEAR_MIN: ClassVar[int] = 0
    YEAR_MAX: ClassVar[int] = 99

    SEQUENCE_MIN: ClassVar[int] = 1
    SEQUENCE_WIDTH: ClassVar[int] = 8

    _PATTERN: ClassVar[re.Pattern[str]] = re.compile(
        r"^(?P<prefix>[A-Z0-9]{1,10})-"
        r"(?P<year>\d{2})-"
        r"(?P<sequence>\d{8})$"
    )

    prefix: TicketPrefix
    year: int
    sequence: int

    def __post_init__(self) -> None:
        if not self.YEAR_MIN <= self.year <= self.YEAR_MAX:
            raise ValueError(f"Year must be in range {self.YEAR_MIN}-{self.YEAR_MAX}.")

        if self.sequence < self.SEQUENCE_MIN:
            raise ValueError("Sequence must be positive.")

    @classmethod
    def parse(cls, string: str) -> Self:
        """Парсит номер заявки из сырой строки."""

        match = cls._PATTERN.fullmatch(string)

        if match is None:
            raise ValueError(
                f"Invalid ticket number: {string!r}. Expected format PREFIX-YY-NNNNNNNN."
            )

        return cls(
            prefix=TicketPrefix(match["prefix"]),
            year=int(match["year"]),
            sequence=int(match["sequence"]),
        )

    def __str__(self) -> str:
        return f"{self.prefix}-{self.year:02d}-{self.sequence:0{self.SEQUENCE_WIDTH}d}"

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}("
            f"prefix={self.prefix!r}, "
            f"year={self.year}, "
            f"sequence={self.sequence})"
        )
