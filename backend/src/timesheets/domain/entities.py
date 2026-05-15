from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from ...shared.domain.entities import Entity
from ...shared.domain.exceptions import InvalidStateError, InvariantViolationError
from ...shared.utils.time import current_datetime
from .events import WorklogApproved, WorklogCreated, WorklogRejected, WorklogSubmitted
from .vo import WorklogStatus


@dataclass(kw_only=True)
class Worklog(Entity):
    """
    Запись о фактически затраченном времени.
    Может относиться к задаче или тикету.
    """

    ticket_id: UUID | None = None
    task_id: UUID | None = None

    user_id: UUID  # тот, кто потратил время
    hours_spent: Decimal
    entry_date: date
    description: str | None = None

    status: WorklogStatus
    approved_by: UUID | None = None
    approved_at: datetime | None = None
    rejection_reason: str | None = None

    def __post_init__(self) -> None:
        # 1. Количество списанных часов не может быть отрицательным
        if self.hours_spent <= 0:
            raise ValueError("Hours spent must be positive")

        # 2. Запись должна принадлежать либо тикету, либо задаче
        if self.ticket_id is None and self.task_id is None:
            raise InvariantViolationError("Worklog must be linked to a ticket or task")

    @classmethod
    def log(
            cls,
            user_id: UUID,
            hours_spent: Decimal,
            entry_date: date,
            description: str | None = None,
            ticket_id: UUID | None = None,
            task_id: UUID | None = None,
    ) -> "Worklog":
        """Создание новой записи о потраченном времени (в статусе DRAFT)"""

        worklog = cls(
            user_id=user_id,
            hours_spent=hours_spent,
            entry_date=entry_date,
            ticket_id=ticket_id,
            task_id=task_id,
            description=description,
            status=WorklogStatus.DRAFT,
        )

        # Регистрация доменного события
        worklog.register_event(
            WorklogCreated(
                worklog_id=worklog.id,
                ticket_id=ticket_id,
                task_id=task_id,
                user_id=user_id,
                hours_spent=float(hours_spent),
                entry_date=entry_date,
            )
        )

        return worklog

    def submit(self) -> None:
        """Отправление записи на согласование"""

        # Отправлять на согласование можно только из черновика
        if self.status != WorklogStatus.DRAFT:
            raise InvalidStateError("Only draft worklogs can be submitted")

        self.status = WorklogStatus.SUBMITTED
        self.updated_at = current_datetime()

        self.register_event(
            WorklogSubmitted(
                worklog_id=self.id,
                ticket_id=self.ticket_id,
                task_id=self.task_id,
                user_id=self.user_id,
            )
        )

    def approve(self, approved_by: UUID) -> None:
        """
        Согласование записи.
        Вызывает событие для обновления факта потраченных часов в задаче.
        """

        if self.status != WorklogStatus.SUBMITTED:
            raise InvalidStateError("Only submitted worklogs can be approved")

        self.status = WorklogStatus.APPROVED
        self.approved_by = approved_by
        self.approved_at = current_datetime()
        self.updated_at = current_datetime()

        self.register_event(
            WorklogApproved(
                worklog_id=self.id,
                ticket_id=self.ticket_id,
                task_id=self.task_id,
                user_id=self.user_id,
                hours_spent=float(self.hours_spent),
                entry_date=self.entry_date,
                approved_by=approved_by,
            )
        )

    def reject(self, rejected_by: UUID, reason: str) -> None:
        """Отклонение записи с указанием причины"""

        if self.status != WorklogStatus.SUBMITTED:
            raise InvalidStateError("Only submitted entries can be rejected")

        self.status = WorklogStatus.REJECTED
        self.rejection_reason = reason
        self.updated_at = current_datetime()

        self.register_event(
            WorklogRejected(
                time_entry_id=self.id,
                rejected_by=rejected_by,
                reason=reason,
            )
        )

    def edit(
            self,
            *,
            hours_spent: Decimal | None = None,
            entry_date: date | None = None,
            description: str | None = None,
    ) -> None:
        """Редактирование записи"""

        if not self.status.is_editable:
            raise InvalidStateError("Worklog in non editable status")

        is_edited = False

        if hours_spent is not None:
            if hours_spent <= 0:
                raise ValueError("Hours spent must be positive")

            self.hours_spent = hours_spent
            is_edited = True

        if entry_date is not None:
            self.entry_date = entry_date
            is_edited = True

        if description is not None:
            self.description = description
            is_edited = True

        if is_edited:
            self.updated_at = current_datetime()
