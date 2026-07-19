from dataclasses import dataclass, field
from uuid import UUID

from src.shared.domain.events import Event
from src.shared.domain.vo import Priority

from .vo import TicketNumber, TicketStatus


@dataclass(frozen=True, kw_only=True)
class TicketCreated(Event):
    """Тикет успешно создан"""

    ticket_id: UUID
    title: str
    number: TicketNumber
    created_by: UUID
    reporter_id: UUID
    priority: Priority
    project_id: UUID | None = None
    counterparty_id: UUID | None = None


@dataclass(frozen=True, kw_only=True)
class TicketEdited(Event):
    """Тикет был изменён."""

    ticket_id: UUID
    number: TicketNumber
    changes: dict[str, list[str]] = field(default_factory=dict)
    edited_by: UUID


@dataclass(frozen=True, kw_only=True)
class TicketApprovalSubmitted(Event):
    """
    Тикет отправлен на согласование.
    """

    ticket_id: UUID
    number: TicketNumber
    submitted_by: UUID
    counterparty_id: UUID | None = None


@dataclass(frozen=True, kw_only=True)
class TicketApproved(Event):
    """
    Тикет был успешно согласован.
    """

    ticket_id: UUID
    number: TicketNumber
    approved_by: UUID
    counterparty_id: UUID | None = None


@dataclass(frozen=True, kw_only=True)
class TicketRejected(Event):
    """Заявка была отклонена на этапе согласования."""

    ticket_id: UUID
    number: TicketNumber
    reporter_id: UUID
    rejected_by: UUID


@dataclass(frozen=True, kw_only=True)
class TicketAssigned(Event):
    """
    Тикет назначен на исполнителя.
    """

    ticket_id: UUID
    number: TicketNumber
    title: str
    assignee_id: UUID | None = None
    assigned_by: UUID
    old_assignee: UUID | None = None


@dataclass(frozen=True, kw_only=True)
class TicketStatusChanged(Event):
    """
    Изменён статус заявки.
    """

    ticket_id: UUID
    number: TicketNumber
    old_status: TicketStatus
    new_status: TicketStatus
    changed_by: UUID


@dataclass(frozen=True, kw_only=True)
class TicketPriorityChanged(Event):
    """Изменён приоритет тикета"""

    ticket_id: UUID
    number: TicketNumber
    changed_by: UUID
    old_priority: Priority
    new_priority: Priority


@dataclass(frozen=True, kw_only=True)
class TicketPaused(Event):
    """
    Тикет был поставлен на паузу.
    """

    ticket_id: UUID
    number: TicketNumber
    reason: str
    paused_by: UUID


@dataclass(frozen=True, kw_only=True)
class TicketResolved(Event):
    """
    Тикет решён.
    """

    ticket_id: UUID
    number: TicketNumber
    reporter_id: UUID
    resolved_by: UUID


@dataclass(frozen=True, kw_only=True)
class TicketClosed(Event):
    """
    Тикет был успешно закрыт.
    """

    ticket_id: UUID
    number: TicketNumber
    reporter_id: UUID
    closed_by: UUID


@dataclass(frozen=True, kw_only=True)
class TicketReopened(Event):
    """
    Тикет был переоткрыт после завершения.
    """

    ticket_id: UUID
    number: TicketNumber
    assignee_id: UUID | None = None
    reopened_by: UUID


@dataclass(frozen=True, kw_only=True)
class TicketCanceled(Event):
    """Тикет был отменён."""

    ticket_id: UUID
    number: TicketNumber
    reporter_id: UUID
    assignee_id: UUID | None = None
    canceled_by: UUID


@dataclass(frozen=True, kw_only=True)
class TicketArchived(Event):
    """Тикет архивирован"""

    ticket_id: UUID
    number: TicketNumber
    reporter_id: UUID
    archived_by: UUID
