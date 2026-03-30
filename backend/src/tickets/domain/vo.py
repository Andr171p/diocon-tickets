from enum import StrEnum

from attr import dataclass, field

from ...shared.domain.vo import ValueObject


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


@dataclass
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
