from dataclasses import dataclass
from uuid import UUID

from ...shared.domain.events import Event
from .vo import TicketPriority

# --- События для проектов ---


@dataclass(frozen=True, kw_only=True)
class ProjectCreated(Event):
    """Проект успешно создан"""

    project_id: UUID
    name: str
    created_by: UUID
    counterparty_id: UUID | None = None

# --- События для тикетов ---


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
