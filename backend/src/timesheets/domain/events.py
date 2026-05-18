from dataclasses import dataclass
from datetime import date
from uuid import UUID

from ...shared.domain.events import Event


@dataclass(frozen=True, kw_only=True)
class WorklogCreated(Event):
    """Создана запись о потраченном времени"""

    worklog_id: UUID
    ticket_id: UUID | None = None
    task_id: UUID | None = None
    user_id: UUID
    hours_spent: float
    entry_date: date


@dataclass(frozen=True, kw_only=True)
class WorklogSubmitted(Event):
    """Запись отправлена на согласование"""

    worklog_id: UUID
    ticket_id: UUID | None = None
    task_id: UUID | None = None
    user_id: UUID


@dataclass(frozen=True, kw_only=True)
class WorklogApproved(Event):
    """Потраченные часы согласованы"""

    worklog_id: UUID
    ticket_id: UUID | None = None
    task_id: UUID | None = None
    user_id: UUID
    hours_spent: float
    entry_date: date
    approved_by: UUID


@dataclass(frozen=True, kw_only=True)
class WorklogRejected(Event):
    """Запись отклонена"""

    worklog_id: UUID
    rejected_by: UUID
    reason: str
