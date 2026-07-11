from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from src.activity_logs.domain.models import ActivityLog
from src.activity_logs.registry import register_activity_log_mapper
from src.shared.domain.events import Event

from .vo import TaskNumber, TaskStatus


@dataclass(frozen=True, kw_only=True)
class TaskCreated(Event):
    """
    Задача создана.
    """

    task_id: UUID
    ticket_id: UUID | None = None
    title: str
    created_by: UUID


@dataclass(frozen=True, kw_only=True)
class TaskStatusChanged(Event):
    """
    Статус задачи изменён.
    """

    task_id: UUID
    ticket_id: UUID | None = None
    old_status: TaskStatus
    new_status: TaskStatus
    changed_by: UUID


@dataclass(frozen=True, kw_only=True)
class TaskAssigned(Event):
    """
    На задачу назначен исполнитель.
    """

    task_id: UUID
    ticket_id: UUID | None = None
    old_assignee: UUID | None = None
    new_assignee: UUID
    assigned_by: UUID


@dataclass(frozen=True, kw_only=True)
class TaskUnassigned(Event):
    """
    Исполнитель снят с задачи.
    """

    task_id: UUID
    number: TaskNumber
    old_assignee: UUID
    unassigned_by: UUID


@dataclass(frozen=True, kw_only=True)
class TaskWorkingStarted(Event):
    """
    Началась работа над задачей.
    """

    task_id: UUID
    number: TaskNumber
    assignee_id: UUID
    working_since: datetime
    started_by: UUID


@dataclass(frozen=True, kw_only=True)
class TaskWorkingFinished(Event):
    """
    Работа над задачей окончена/приостановлена.
    """

    task_id: UUID
    number: TaskNumber
    assignee_id: UUID
    actual_hours: Decimal
    finished_by: UUID


@dataclass(frozen=True, kw_only=True)
class TaskReviewRequested(Event):
    """
    Исполнитель запросил проверку своей задачи.
    """

    task_id: UUID
    ticket_id: UUID | None = None
    reviewer_id: UUID
    requested_by: UUID
    old_reviewer: UUID | None = None


@dataclass(frozen=True, kw_only=True)
class TaskCompleted(Event):
    """
    Задача успешно выполнена.
    """

    task_id: UUID
    number: TaskNumber
    completed_by: UUID
    completed_at: datetime


@dataclass(frozen=True, kw_only=True)
class TaskArchived(Event):
    """
    Задачи перенесена в архив.
    """

    task_id: UUID
    ticket_id: UUID | None = None
    created_by: UUID
    archived_by: UUID


@register_activity_log_mapper(TaskCreated)
def map_task_created_to_activity_log(event: TaskCreated) -> ActivityLog:
    return ActivityLog(
        aggregate_type="task",
        aggregate_id=event.task_id,
        action="task.created",
        actor_id=event.created_by,
        event_id=event.event_id,
    )


@register_activity_log_mapper(TaskStatusChanged)
def map_task_status_changed_to_activity_log(event: TaskStatusChanged) -> ActivityLog:
    return ActivityLog(
        aggregate_type="task",
        aggregate_id=event.task_id,
        action="task.status_changed",
        actor_id=event.changed_by,
        changes={"old_status": event.old_status, "new_status": event.new_status},
    )


@register_activity_log_mapper(TaskAssigned)
def map_task_assigned_to_activity_log(event: TaskAssigned) -> ActivityLog:
    return ActivityLog(
        aggregate_type="task",
        aggregate_id=event.task_id,
        action="task.assigned",
        actor_id=event.assigned_by,
        changes={"old_assignee": event.old_assignee, "new_assignee": event.new_assignee},
    )


@register_activity_log_mapper(TaskUnassigned)
def map_task_unassigned_to_activity_log(event: TaskUnassigned) -> ActivityLog:
    return ActivityLog(
        aggregate_type="task",
        aggregate_id=event.task_id,
        action="task.unassigned",
        actor_id=event.unassigned_by,
        changes={"old_assignee": event.old_assignee}
    )
