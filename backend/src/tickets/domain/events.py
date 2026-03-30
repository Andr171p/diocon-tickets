from dataclasses import dataclass

from ...shared.domain.events import Event


@dataclass(frozen=True, kw_only=True)
class TicketCreated(Event):
    """Тикет успешно создан"""


@dataclass(frozen=True, kw_only=True)
class TicketStatusChanged(Event):
    """Статус тикета был изменён"""


@dataclass(frozen=True, kw_only=True)
class TicketAssigned(Event):
    """Тикет назначен исполнителю"""
