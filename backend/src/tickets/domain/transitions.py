from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .entities import Ticket

from uuid import UUID

from .transition_factory import register_transition, transition
from .vo import TicketAction, TicketStatus

# Отправить на согласование
register_transition(
    TicketStatus.NEW,
    action=TicketAction.SUBMIT_FOR_APPROVAL,
    to=TicketStatus.PENDING_APPROVAL,
)

# Начать трекать тикет
register_transition(
    TicketStatus.OPEN,
    TicketStatus.PAUSED,
    TicketStatus.WAITING,
    action=TicketAction.START_PROGRESS,
    to=TicketStatus.IN_PROGRESS,
)

# Пере-открытие тикета
register_transition(TicketStatus.RESOLVED, action=TicketAction.REOPEN, to=TicketStatus.REOPENED)

# Поставить тикет на паузу
register_transition(TicketStatus.IN_PROGRESS, action=TicketAction.PAUSE, to=TicketStatus.PAUSED)

# Отмена тикета
register_transition(
    TicketStatus.NEW,
    TicketStatus.OPEN,
    TicketStatus.IN_PROGRESS,
    TicketStatus.PAUSED,
    TicketStatus.WAITING,
    action=TicketAction.CANCEL,
    to=TicketStatus.CANCELED,
)

# Отклонение тикета
register_transition(
    TicketStatus.PENDING_APPROVAL, action=TicketAction.REJECT, to=TicketStatus.REJECTED,
)

# Редактирование тикета
register_transition(
    TicketStatus.NEW,
    TicketStatus.PENDING_APPROVAL,
    TicketStatus.OPEN,
    TicketStatus.REOPENED,
    action=TicketAction.EDIT,
)

# Ожидание обратной связи клиента
register_transition(
    TicketStatus.IN_PROGRESS,
    TicketStatus.PAUSED,
    action=TicketAction.WAIT,
    to=TicketStatus.WAITING,
)

# Повторная отправка на согласование
register_transition(
    TicketStatus.REJECTED,
    action=TicketAction.SUBMIT_FOR_APPROVAL,
    to=TicketStatus.PENDING_APPROVAL,
)


@transition(
    TicketStatus.OPEN,
    TicketStatus.IN_PROGRESS,
    TicketStatus.WAITING,
    TicketStatus.REOPENED,
    TicketStatus.RESOLVED,
    action=TicketAction.ASSIGN,
)
def on_ticket_assign(ticket: Ticket, assigned_by: UUID, assignee_id: UUID) -> None:
    ticket.apply_assignment(assignee_id, assigned_by)


@transition(TicketStatus.RESOLVED, action=TicketAction.CLOSE, to=TicketStatus.CLOSED)
def on_ticket_close(ticket: Ticket, closed_by: UUID) -> None:
    ticket.mark_closed(closed_by)


@transition(TicketStatus.PENDING_APPROVAL, action=TicketAction.APPROVE, to=TicketStatus.OPEN)
def on_ticket_approve(ticket: Ticket, approved_by: UUID) -> None:
    ticket.mark_approved(approved_by)


@transition(
    TicketStatus.RESOLVED,
    TicketStatus.CLOSED,
    action=TicketAction.REOPEN,
    to=TicketStatus.REOPENED,
)
def on_ticket_reopen(ticket: Ticket, reopened_by: UUID) -> None:  # noqa: ARG001
    ticket.clear_resolution()
    ticket.clear_closing()


@transition(
    TicketStatus.IN_PROGRESS,
    TicketStatus.WAITING,
    action=TicketAction.RESOLVE,
    to=TicketStatus.RESOLVED,
)
def on_ticket_resolve(ticket: Ticket, resolved_by: UUID) -> None:
    ticket.mark_resolved(resolved_by)
