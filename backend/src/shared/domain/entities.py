import abc
import uuid
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime

from ..utils.time import current_datetime
from .events import Event


@dataclass
class Entity(abc.ABC):
    """
    Базовая доменная сущность, от которой наследуются все остальные бизнес модели.
    Идентичность определяется уникальным ID, а не аттрибутами модели.
    """

    _events: list[Event] = field(default_factory=list, init=False)

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=current_datetime)
    updated_at: datetime = field(default_factory=current_datetime)

    def __eq__(self, other) -> bool:
        if not isinstance(other, Entity):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    def collect_events(self) -> Iterator[Event]:
        while self._events:
            yield self._events.pop(0)


@dataclass
class AggregateRoot(Entity):
    """
    Корень агрегата - кластер доменных объектов, агрегат управляет их поведением и состоянием
    """
