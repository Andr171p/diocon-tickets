from dataclasses import dataclass
from uuid import UUID

from src.shared.domain.events import Event

from .vo import CommentType, Priority, ReactionType, TicketNumber, TicketStatus


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
class TicketApprovalRequested(Event):
    """
    Для тикета было запросили согласование.
    """

    ticket_id: UUID
    number: TicketNumber
    requested_by: UUID
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
    ticket_number: TicketNumber
    reason: str
    paused_by: UUID


@dataclass(frozen=True, kw_only=True)
class TicketResolved(Event):
    """
    Тикет решён.
    """

    ticket_id: UUID
    number: TicketNumber
    resolved_by: UUID


@dataclass(frozen=True, kw_only=True)
class TicketClosed(Event):
    """
    Тикет был успешно закрыт.
    """

    ticket_id: UUID
    number: TicketNumber
    closed_by: UUID


@dataclass(frozen=True, kw_only=True)
class TicketReopened(Event):
    """
    Тикет был переоткрыт после завершения.
    """

    ticket_id: UUID
    number: TicketNumber
    reopened_by: UUID


@dataclass(frozen=True, kw_only=True)
class TicketArchived(Event):
    """Тикет архивирован"""

    ticket_id: UUID
    number: TicketNumber
    reporter_id: UUID
    archived_by: UUID


@dataclass(frozen=True, kw_only=True)
class CommentAdded(Event):
    """Добавлен комментарий"""

    ticket_id: UUID
    comment_id: UUID
    author_id: UUID
    comment_type: CommentType
    is_public: bool


@dataclass(frozen=True, kw_only=True)
class CommentEdited(Event):
    """Комментарий отредактирован"""

    ticket_id: UUID
    comment_id: UUID
    edited_by: UUID


@dataclass(frozen=True, kw_only=True)
class ReactionAdded(Event):
    """Реакция поставлена"""

    comment_id: UUID
    author_id: UUID
    reaction_type: ReactionType
