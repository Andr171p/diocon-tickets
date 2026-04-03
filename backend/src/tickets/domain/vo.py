from typing import ClassVar, Self

from dataclasses import dataclass, field
from enum import StrEnum
from uuid import UUID

from ...shared.domain.vo import ValueObject
from ...shared.utils.time import current_datetime


class TicketStatus(StrEnum):
    """Возможные статусы тикета"""

    NEW = "Новый"
    OPEN = "Открыт"
    IN_PROGRESS = "В работе"
    WAITING = "Ожидает ответа"
    RESOLVED = "Решён"
    CLOSED = "Закрыт"
    REOPENED = "Переоткрыт"


class TicketPriority(StrEnum):
    """Приоритет тикета"""

    LOW = "Низкий"
    MEDIUM = "Средний"
    HIGH = "Высокий"
    CRITICAL = "Критический"  # Время реакции поддержки - мгновенное


@dataclass(frozen=True, kw_only=True)
class Tag(ValueObject):
    """
    Теги - метки (ключевые слова), которые можно присваивать тикетам для дополнительной,
    неструктурированной классификации.
    """

    name: str
    color: str = field(default="#3498db")

    def __str__(self) -> str:
        return self.name


class CommentType(StrEnum):
    """Тип комментария"""

    PUBLIC = "public"  # виден всем
    INTERNAL = "internal"  # виден только сотрудникам поддержки
    NOTE = "note"  # виден только автору


@dataclass(frozen=True)
class TicketNumber(ValueObject):
    """
    Уникальный номер тикета в формате - XXX-YYYY-NNNNNNNN

    Примеры:
     - РОМ-26-00012456
     - INT-26-00004521
     - ЯНД-26-00123769
    """

    INTERNAL_PREFIX: ClassVar[str] = "INT"
    SEQUENCE_LENGTH: ClassVar[int] = 8
    YEAR_LENGTH: ClassVar[int] = 2
    PREFIX_LENGTH: ClassVar[int] = 3
    NUMBER_PARTS: ClassVar[int] = 3

    value: str

    def __post_init__(self) -> None:

        # 1. Номер не должен быть пустым
        if not self.value:
            raise ValueError("Ticket number cannot be empty")

        # 2. Проверка формата
        if not self._is_valid_format(self.value):
            raise ValueError(
                f"Invalid ticket number format: {self.value}. "
                f"Expected format: XXX-YY-NNNNNN (example: РОМ-26-00012456)"
            )

    @classmethod
    def _is_valid_format(cls, number: str) -> bool:
        """Проверка формата XXX-YY-NNNNNNNN"""

        if len(number) != cls.PREFIX_LENGTH + 1 + cls.YEAR_LENGTH + 1 + cls.SEQUENCE_LENGTH:
            return False

        parts = number.split("-")
        if len(parts) != cls.NUMBER_PARTS:
            return False

        prefix, year, seq = parts

        return (
            len(prefix) == cls.PREFIX_LENGTH
            and prefix.isalnum()
            and len(year) == cls.YEAR_LENGTH
            and year.isdigit()
            and len(seq) == cls.SEQUENCE_LENGTH
            and seq.isdigit()
        )

    @classmethod
    def create(cls, ticket_id: UUID, counterparty_name: str | None = None) -> Self:
        """Создание уникального номера тикета"""

        # 1. Создание префикса. INT - для внутренних тикетов
        if counterparty_name is None or not counterparty_name.strip():
            prefix = cls.INTERNAL_PREFIX
        else:
            prefix = counterparty_name.strip()[: cls.PREFIX_LENGTH].upper()
            if len(prefix) < cls.PREFIX_LENGTH:
                prefix = prefix.ljust(cls.PREFIX_LENGTH, "X")

        # 2. Создание кода для текущего года
        year_short = current_datetime().year % 100

        # 2. Генерация последовательности цифр
        sequence = f"{ticket_id.int}"[-cls.SEQUENCE_LENGTH:].zfill(cls.SEQUENCE_LENGTH)
        number = f"{prefix}-{year_short:02d}-{sequence}"

        return cls(value=number)

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"TicketNumber({self.value!r})"

    @property
    def prefix(self) -> str:
        """Префикс (РОМ, INT, ЯНД и т.д.)"""

        return self.value.split("-")[0]

    @property
    def year_short(self) -> int:
        """Год (две последние цифры)"""

        return int(self.value.split("-")[1])

    @property
    def sequence(self) -> str:
        """Порядковый номер"""

        return self.value.split("-")[2]

    @property
    def is_internal(self) -> bool:
        """Является ли тикет внутренним"""

        return self.prefix == self.INTERNAL_PREFIX
