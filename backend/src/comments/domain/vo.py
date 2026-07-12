from dataclasses import dataclass
from enum import StrEnum, auto
from uuid import UUID

from src.shared.domain.vo import ValueObject


class AggregateType(StrEnum):
    """Агрегаты к которым можно оставлять комментарии."""

    TICKET = auto()
    TASK = auto()


@dataclass(frozen=True, slots=True)
class AggregateReference(ValueObject):
    """Ссылка на агрегат к которому оставлен комментарий."""

    id: UUID
    type: AggregateType


class CommentVisibility(StrEnum):
    """Область видимости комментария."""

    PUBLIC = auto()  # виден всем
    INTERNAL = auto()  # виден только сотрудникам поддержки
    NOTE = auto()  # виден только автору
