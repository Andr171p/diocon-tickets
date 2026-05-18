from typing import ClassVar

from dataclasses import dataclass
from enum import StrEnum

from ...shared.domain.vo import ValueObject
from ...tickets.domain.vo import TicketNumber


class TaskStatus(StrEnum):
    """Статус выполнения задачи"""

    BACKLOG = "backlog"  # ещё сырая задача
    TODO = "todo"  # готова к выполнению
    IN_PROGRESS = "in_progress"  # в работе
    BLOCKED = "blocked"  # заблокирована (приостановлена)
    REVIEW = "review"  # отправлена на ревью
    DONE = "done"  # выполнена
    CANCELLED = "cancelled"  # отменена

    @property
    def is_open(self) -> bool:
        return self not in {TaskStatus.DONE, TaskStatus.CANCELLED}

    @property
    def is_finished(self) -> bool:
        return self in {TaskStatus.DONE, TaskStatus.CANCELLED}


@dataclass(frozen=True)
class StoryPoints(ValueObject):
    """
    Относительные единицы измерения в Agile и Scrum,
    которые отражают общую сложность, объем работы и риски выполнения задачи.
    """

    ALLOWED_VALUES: ClassVar[set[int]] = {1, 2, 3, 5, 8, 13, 21}

    value: int

    def __post_init__(self) -> None:
        if self.value not in self.ALLOWED_VALUES:
            raise ValueError(
                f"Invalid story point value: {self.value}. "
                f"Use numbers from a series: {self.ALLOWED_VALUES}"
            )

    def __str__(self) -> str:
        return f"{self.value} SP"


@dataclass(frozen=True)
class TaskNumber(ValueObject):
    """
    Уникальный человеко-читаемый номер задачи в формате - TICKET_NUMBER-SEQUENCE
    """

    value: str

    SEQUENCE_LENGTH: ClassVar[int] = 3
    INTERNAL_PREFIX: ClassVar[str] = "TASK"  # для задач без тикета
    NUMBER_PARTS: ClassVar[int] = 2

    def __post_init__(self) -> None:
        if not self.value.strip() or not self.is_valid_format(self.value):
            raise ValueError(f"Invalid TaskNumber format: {self.value}")

    @classmethod
    def is_valid_format(cls, number: str) -> bool:
        """Проверка формата номера задачи"""

        parts = number.rsplit("-", 1)
        if len(parts) != cls.NUMBER_PARTS:
            return False

        prefix, sequence = parts

        return (
            len(sequence) == cls.SEQUENCE_LENGTH and
            sequence.isdigit() and
            (
                TicketNumber.is_valid_format(prefix) or
                prefix == cls.INTERNAL_PREFIX
            )
        )

    @classmethod
    def create(
            cls, ticket_number: TicketNumber | None = None, sequence: int = 1
    ) -> "TaskNumber":
        """Создание номера задачи"""

        # 1. Длина последовательности не может быть меньше 1
        if sequence < 0:
            raise ValueError("Task sequence must be positive")

        sequence_str = f"{sequence:0{cls.SEQUENCE_LENGTH}d}"

        if ticket_number is not None:
            return cls(f"{ticket_number}-{sequence_str}")

        return cls(f"{cls.INTERNAL_PREFIX}-{sequence_str}")

    @property
    def is_internal(self) -> bool:
        """Задача не привязана к тикету"""

        return self.value.startswith(self.INTERNAL_PREFIX)

    @property
    def ticket_number(self) -> TicketNumber | None:
        """Номер родительского тикета"""

        if self.is_internal:
            return None

        ticket_part = self.value.rsplit("-", 1)[0]
        return TicketNumber(ticket_part)

    @property
    def sequence(self) -> int:
        """Порядковый номер задачи"""

        return int(self.value.rsplit("-", 1)[1])
