from dataclasses import dataclass
from uuid import UUID

from ...shared.domain.events import Event
from .vo import TaskStatus


@dataclass(frozen=True, kw_only=True)
class TaskCreated(Event):
    """Задача создана"""

    task_id: UUID
    ticket_id: UUID | None = None
    title: str
    created_by: UUID


@dataclass(frozen=True, kw_only=True)
class TaskStatusMoved(Event):
    """Статус задачи изменён"""

    task_id: UUID
    ticket_id: UUID | None = None
    old_status: TaskStatus
    new_status: TaskStatus
    moved_by: UUID


@dataclass(frozen=True, kw_only=True)
class TaskAssigned(Event):
    """На задачу назначен исполнитель"""

    task_id: UUID
    ticket_id: UUID | None = None
    old_assignee: UUID
    new_assignee: UUID
    assigned_by: UUID


@dataclass(frozen=True, kw_only=True)
class TaskReviewRequested(Event):
    """Исполнитель запросил проверку своей задачи"""

    task_id: UUID
    ticket_id: UUID | None = None
    reviewer_id: UUID
    requested_by: UUID
    old_reviewer: UUID | None = None


@dataclass(frozen=True, kw_only=True)
class TaskArchived(Event):
    """Задачи заархивирована"""

    task_id: UUID
    ticket_id: UUID | None = None
    created_by: UUID
    archived_by: UUID
