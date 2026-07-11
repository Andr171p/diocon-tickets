"""
Преобразование доменных событий в человекочитаемые бизнес действия.
"""

from src.activity_logs.domain.models import ActivityLog
from src.activity_logs.registry import register_activity_log_mapper

from .entities import Ticket
from .events import (
    TicketApprovalSubmitted,
    TicketApproved,
    TicketArchived,
    TicketAssigned,
    TicketCanceled,
    TicketClosed,
    TicketCreated,
    TicketEdited,
    TicketPaused,
    TicketPriorityChanged,
    TicketReopened,
    TicketResolved,
    TicketStatusChanged,
)

AGGREGATE_TYPE = Ticket.__name__.lower()


@register_activity_log_mapper(TicketCreated)
def map_ticket_created_to_activity_log(event: TicketCreated) -> ActivityLog:
    return ActivityLog(
        aggregate_type=AGGREGATE_TYPE,
        aggregate_id=event.ticket_id,
        action="ticket.created",
        actor_id=event.created_by,
        event_id=event.event_id,
    )


@register_activity_log_mapper(TicketApprovalSubmitted)
def map_ticket_approval_submitted_to_activity_log(event: TicketApprovalSubmitted) -> ActivityLog:
    return ActivityLog(
        aggregate_type=AGGREGATE_TYPE,
        aggregate_id=event.ticket_id,
        action="ticket.approval_submitted",
        actor_id=event.submitted_by,
        event_id=event.event_id,
    )


@register_activity_log_mapper(TicketApproved)
def map_ticket_approved_to_activity_log(event: TicketApproved) -> ActivityLog:
    return ActivityLog(
        aggregate_type=AGGREGATE_TYPE,
        aggregate_id=event.ticket_id,
        action="ticket.approved",
        actor_id=event.approved_by,
        event_id=event.event_id,
    )


@register_activity_log_mapper(TicketAssigned)
def map_ticket_assigned_to_activity_log(event: TicketAssigned) -> ActivityLog:
    return ActivityLog(
        aggregate_type=AGGREGATE_TYPE,
        aggregate_id=event.ticket_id,
        action="ticket.assigned",
        actor_id=event.assigned_by,
        changes={"old_assignee": event.old_assignee, "new_assignee": event.assignee_id},
        event_id=event.event_id,
    )


@register_activity_log_mapper(TicketStatusChanged)
def map_ticket_status_changed_to_activity_log(event: TicketStatusChanged) -> ActivityLog:
    return ActivityLog(
        aggregate_type=AGGREGATE_TYPE,
        aggregate_id=event.ticket_id,
        action="ticket.status_changed",
        actor_id=event.changed_by,
        changes={"old_status": event.old_status.value, "new_status": event.new_status.value},
        event_id=event.event_id,
    )


@register_activity_log_mapper(TicketPriorityChanged)
def map_ticket_priority_changed_to_activity_log(event: TicketPriorityChanged) -> ActivityLog:
    return ActivityLog(
        aggregate_type="ticket",
        aggregate_id=event.ticket_id,
        action="ticket.priority_changed",
        actor_id=event.changed_by,
        changes={
            "old_priority": event.old_priority.value, "new_priority": event.new_priority.value
        },
        event_id=event.event_id,
    )


@register_activity_log_mapper(TicketPaused)
def map_ticket_paused_to_activity_log(event: TicketPaused) -> ActivityLog:
    return ActivityLog(
        aggregate_type="ticket",
        aggregate_id=event.ticket_id,
        action="ticket.paused",
        actor_id=event.paused_by,
        changes={"reason": event.reason},
        event_id=event.event_id,
    )


@register_activity_log_mapper(TicketResolved)
def map_ticket_resolved_to_activity_log(event: TicketResolved) -> ActivityLog:
    return ActivityLog(
        aggregate_type="ticket",
        aggregate_id=event.ticket_id,
        action="ticket.resolved",
        actor_id=event.resolved_by,
        event_id=event.event_id,
    )


@register_activity_log_mapper(TicketClosed)
def map_ticket_closed_to_activity_log(event: TicketClosed) -> ActivityLog:
    return ActivityLog(
        aggregate_type="ticket",
        aggregate_id=event.ticket_id,
        action="ticket.closed",
        actor_id=event.closed_by,
        event_id=event.event_id,
    )


@register_activity_log_mapper(TicketReopened)
def map_ticket_reopened_to_activity_log(event: TicketReopened) -> ActivityLog:
    return ActivityLog(
        aggregate_type="ticket",
        aggregate_id=event.ticket_id,
        action="ticket.reopened",
        actor_id=event.reopened_by,
        event_id=event.event_id,
    )


@register_activity_log_mapper(TicketCanceled)
def map_ticket_canceled_to_activity_log(event: TicketCanceled) -> ActivityLog:
    return ActivityLog(
        aggregate_type="ticket",
        aggregate_id=event.ticket_id,
        action="ticket.canceled",
        actor_id=event.canceled_by,
        event_id=event.event_id,
    )


@register_activity_log_mapper(TicketArchived)
def map_ticket_archived_to_activity_log(event: TicketArchived) -> ActivityLog:
    return ActivityLog(
        aggregate_type="ticket",
        aggregate_id=event.ticket_id,
        action="ticket.archived",
        actor_id=event.archived_by,
        event_id=event.event_id,
    )


@register_activity_log_mapper(TicketEdited)
def map_ticket_edited_to_activity_log(event: TicketEdited) -> ActivityLog:
    return ActivityLog(
        aggregate_type=AGGREGATE_TYPE,
        aggregate_id=event.ticket_id,
        action="ticket.edited",
        changes=event.changes,
        actor_id=event.edited_by,
        event_id=event.event_id,
    )
