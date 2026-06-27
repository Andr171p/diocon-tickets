from typing import Annotated, Self

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from typing_extensions import Doc

from src.media.domain.entities import Attachment
from src.shared.domain.entities import AggregateRoot
from src.shared.domain.exceptions import InvalidStateError, InvariantViolationError
from src.shared.domain.vo import Priority, Tag
from src.shared.utils.time import current_datetime

from .consts import (
    ALLOWED_ASSIGN_STATUSES,
    ALLOWED_EDIT_STATUSES,
    REVIEW_DECISION_TO_TASK_STATUS_MAP,
)
from .events import (
    TaskArchived,
    TaskAssigned,
    TaskCompleted,
    TaskCreated,
    TaskReviewRequested,
    TaskStatusChanged,
    TaskUnassigned,
    TaskWorkingFinished,
    TaskWorkingStarted,
)
from .vo import ReviewDecision, StoryPoints, TaskNumber, TaskStatus
from .workflow import task_workflow

SECS_IN_HOURS = 3600.0


@dataclass(kw_only=True)
class Task(AggregateRoot):
    """
    Задача для сотрудника.
    Используется для детализации работ, например по большому тикету.
    """

    ticket_id: UUID | None = None
    project_id: UUID | None = None

    number: TaskNumber
    title: str
    description: str | None = None

    status: TaskStatus
    priority: Priority
    story_points: Annotated[
        StoryPoints | None, Doc("Условная единица для оценки объёма работ")
    ] = None

    assignee_id: Annotated[UUID | None, Doc("Исполнитель задачи")] = None
    reviewer_id: Annotated[UUID | None, Doc("Тот кто проверяет задачу")] = None

    estimated_hours: Annotated[Decimal | None, Doc("Предварительные трудозатраты (часы)")] = None
    actual_hours: Annotated[Decimal, Doc("Факт потраченных часов")] = Decimal(0)

    due_date: Annotated[date | None, Doc("Дедлайн")] = None

    started_at: Annotated[datetime | None, Doc("Время начала выполнения")] = None
    completed_at: Annotated[datetime | None, Doc("Время завершения")] = None
    working_since: Annotated[
        datetime | None, Doc("Время начала работы последней рабочей сессии")
    ] = None

    created_by: UUID

    tags: set[Tag] = field(default_factory=set)

    attachments: list[Attachment] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValueError("Task title cannot be empty")

        if self.description is not None and not self.description.strip():
            raise ValueError("Task description cannot be empty")

        # Задача не может быть в процессе выполнения без исполнителя
        if self.status == TaskStatus.IN_PROGRESS and self.assignee_id is None:
            raise InvariantViolationError(
                "Task cannot be in 'IN_PROGRESS' status without an assignee"
            )

        # Завершённая задача должна иметь дату завершения
        if self.status == TaskStatus.DONE and self.completed_at is None:
            raise InvariantViolationError("Task in 'DONE' status must have completed_at")

    @classmethod
    def create(
            cls,
            number: TaskNumber,
            title: str,
            created_by: UUID,
            description: str | None = None,
            priority: Priority = Priority.MEDIUM,
            ticket_id: UUID | None = None,
            project_id: UUID | None = None,
            due_date: date | None = None,
            estimated_hours: Decimal | None = None,
            tags: list[Tag] | None = None,
    ) -> Self:
        task_id = uuid4()
        title = title.strip()
        description = None if description is None else description.strip()
        estimated_hours = None if estimated_hours is None else Decimal(estimated_hours)
        unique_tags = set() if tags is None else set(tags)

        task = cls(
            id=task_id,
            ticket_id=ticket_id,
            project_id=project_id,
            number=number,
            title=title,
            description=description,
            status=TaskStatus.BACKLOG,
            priority=priority,
            due_date=due_date,
            estimated_hours=estimated_hours,
            created_by=created_by,
            tags=unique_tags,
        )
        task.register_event(
            TaskCreated(
                task_id=task_id,
                ticket_id=ticket_id,
                title=title,
                created_by=created_by,
            )
        )
        return task

    def change_status(self, new_status: TaskStatus, changed_by: UUID) -> None:
        """
        Изменение статуса задачи.
        """

        if new_status == self.status:
            return

        transition = task_workflow.resolve(self.status, new_status)
        for action in transition.actions:
            action(self, changed_by)

        old_status = self.status
        self.status = new_status
        self.updated_at = current_datetime()

        self.register_event(
            TaskStatusChanged(
                task_id=self.id,
                ticket_id=self.ticket_id,
                old_status=old_status,
                new_status=new_status,
                changed_by=changed_by,
            )
        )

    def assign_to(self, assignee_id: UUID, assigned_by: UUID) -> None:
        """
        Назначить исполнителя на задачу.
        """

        if self.assignee_id == assignee_id:
            return

        if self.status not in ALLOWED_ASSIGN_STATUSES:
            raise InvalidStateError(
                f"Cannot assign task in status '{self.status.value}'. "
                f"Allowed statuses: {', '.join(s.value for s in ALLOWED_ASSIGN_STATUSES)}"
            )

        old_assignee = self.assignee_id
        self.assignee_id = assignee_id
        self.updated_at = current_datetime()

        self.register_event(
            TaskAssigned(
                task_id=self.id,
                ticket_id=self.ticket_id,
                old_assignee=old_assignee,
                new_assignee=assignee_id,
                assigned_by=assigned_by,
            )
        )

    def edit(  # noqa: C901
            self,
            *,
            title: str | None = None,
            description: str | None = None,
            priority: Priority | None = None,
            story_points: int | None = None,
            estimated_hours: Decimal | None = None,
            due_date: date | None = None,
    ) -> None:
        """Редактирование задачи"""

        # 1. Редактирование задачи разрешено только в начальных статусах
        if self.status not in ALLOWED_EDIT_STATUSES:
            raise InvalidStateError(
                f"Cannot edit task in status '{self.status.value}'. "
                f"Editing is only allowed in: "
                f"{', '.join(status.value for status in ALLOWED_EDIT_STATUSES)}"
            )

        # 2. Нельзя редактировать архивированную задачу
        if self.is_deleted:
            raise InvalidStateError("Cannot edit deleted task")

        # 3. Применение изменений
        is_edited = False

        if title is not None:
            if not title.strip():
                raise ValueError("Task title cannot be empty")

            self.title = title.strip()
            is_edited = True

        if description is not None:
            if not description.strip():
                raise ValueError("Task description cannot be empty")

            self.description = description.strip()
            is_edited = True

        if priority is not None and priority != self.priority:
            self.priority = priority
            is_edited = True

        if story_points is not None:
            new_story_points = StoryPoints(story_points)

            if self.story_points != new_story_points:
                self.story_points = new_story_points
                is_edited = True

        if estimated_hours is not None:
            if estimated_hours < 0:
                raise ValueError("Estimated hours cannot be negative")

            if estimated_hours != self.estimated_hours:
                self.estimated_hours = estimated_hours
                is_edited = True

        if due_date is not None and due_date != self.due_date:
            self.due_date = due_date
            is_edited = True

        if is_edited:
            self.updated_at = current_datetime()

    def add_actual_hours(self, hours: Decimal) -> None:
        """
        Добавить фактические часы.
        Обновляет счётчик трудозатрат.
        """

        if hours <= 0:
            raise ValueError("Hours must be positive")

        if self.is_deleted:
            raise InvalidStateError("Cannot add hours to archived task")

        self.actual_hours += hours
        self.updated_at = current_datetime()

    def request_review(self, reviewer_id: UUID, requested_by: UUID) -> None:
        """
        Запросить ревью задачи у другого пользователя.
        """

        if self.assignee_id == reviewer_id:
            raise ValueError("Reviewer cannot be the same as assignee")

        old_reviewer = self.reviewer_id
        self.reviewer_id = reviewer_id
        self.updated_at = current_datetime()

        self.change_status(TaskStatus.TO_REVIEW, requested_by)

        self.register_event(
            TaskReviewRequested(
                task_id=self.id,
                ticket_id=self.ticket_id,
                reviewer_id=reviewer_id,
                requested_by=requested_by,
                old_reviewer=old_reviewer,
            )
        )

    def complete_review(self, decision: ReviewDecision, reviewed_by: UUID) -> None:
        """
        Повести ревью задачи.
        """

        next_status = REVIEW_DECISION_TO_TASK_STATUS_MAP[decision]
        self.change_status(next_status, reviewed_by)

    def archive(self, archived_by: UUID) -> None:
        """
        Архивирование задачи (мягкое удаление).
        """

        if self.is_deleted:
            return

        self.deleted_at = current_datetime()

        self.register_event(
            TaskArchived(
                task_id=self.id,
                ticket_id=self.ticket_id,
                created_by=self.created_by,
                archived_by=archived_by,
            )
        )

    def start_work(self, started_by: UUID) -> None:
        """
        Начать работу над задачей.
        Не меняет статус - отвечает только за начало рабочй сессии.
        """

        if self.assignee_id is None:
            raise InvariantViolationError(
                "Task cannot enter a working status without an assignee."
            )

        if self.started_at is None:
            self.started_at = current_datetime()

        if self.working_since is not None:
            return

        self.working_since = current_datetime()

        self.register_event(
            TaskWorkingStarted(
                task_id=self.id,
                number=self.number,
                assignee_id=self.assignee_id,
                working_since=self.working_since,
                started_by=started_by,
            )
        )

    def finish_work(self, finished_by: UUID) -> None:
        """
        Завершение работы над задачей, производит расчёт затраченного времени.
        """

        if self.started_at is None or self.working_since is None:
            return

        if self.assignee_id is None:
            raise InvalidStateError("Cannot finish unassigned task")

        now = current_datetime()
        duration = (now - self.working_since).total_seconds() / SECS_IN_HOURS
        self.actual_hours += Decimal(f"{duration}")

        self.working_since = None

        self.register_event(
            TaskWorkingFinished(
                task_id=self.id,
                number=self.number,
                assignee_id=self.assignee_id,
                actual_hours=self.actual_hours,
                finished_by=finished_by,
            )
        )

    def complete(self, completed_by: UUID) -> None:
        """
        Выполнить задачу (фиксирует финально время).
        """

        if self.completed_at is None:
            self.completed_at = current_datetime()

        self.register_event(
            TaskCompleted(
                task_id=self.id,
                number=self.number,
                completed_by=completed_by,
                completed_at=self.completed_at,
            )
        )

    def reopen(self) -> None:
        """
        Переоткрыть задачу - задача была выполнена и снова вернулась в работу.
        """

        self.completed_at = None
        self.started_at = current_datetime()

    def reset_reviewer(self) -> None:
        """
        Убрать ревьювера с задачи.
        """

        self.reviewer_id = None

    def unassign(self, unassigned_by: UUID) -> None:
        """
        Снять исполнителя с задачи.
        """

        if self.assignee_id is None:
            return

        old_assignee = self.assignee_id
        self.assignee_id = None

        self.register_event(
            TaskUnassigned(
                task_id=self.id,
                number=self.number,
                old_assignee=old_assignee,
                unassigned_by=unassigned_by,
            )
        )
