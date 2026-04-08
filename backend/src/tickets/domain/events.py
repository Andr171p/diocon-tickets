from dataclasses import dataclass
from uuid import UUID

from ...shared.domain.events import Event
from .vo import TicketPriority


@dataclass(frozen=True, kw_only=True)
class TicketCreated(Event):
    """Тикет успешно создан"""

    ticket_id: UUID
    title: str
    created_by: UUID
    reporter_id: UUID
    priority: TicketPriority
    counterparty_id: UUID | None = None


@dataclass(frozen=True, kw_only=True)
class TicketStatusChanged(Event):
    """Статус тикета был изменён"""


@dataclass(frozen=True, kw_only=True)
class TicketAssigned(Event):
    """Тикет назначен исполнителю"""
