from typing import Annotated, Self

from dataclasses import dataclass, field
from datetime import date, datetime
from uuid import UUID

from typing_extensions import Doc

from src.shared.domain.entities import AggregateRoot, Entity
from src.shared.domain.exceptions import InvalidStateError, InvariantViolationError
from src.shared.utils.time import current_datetime

from .events import (
    ProjectArchived,
    ProjectCreated,
    ProjectMemberCreated,
    ProjectMemberRemoved,
)
from .vo import ProjectKey, ProjectRole, ProjectStageStatus, ProjectStatus


@dataclass(kw_only=True)
class ProjectMember(Entity):
    """
    Участник проекта, имеет ограниченный набор ролей в рамках одного проекта.
    """

    project_id: UUID
    project_roles: list[ProjectRole]
    user_id: UUID
    created_by: UUID

    def has_role(self, project_role: ProjectRole) -> bool:
        return project_role in self.project_roles

    def grant_role(self, project_role: ProjectRole) -> None:
        if project_role in self.project_roles:
            return

        self.project_roles.append(project_role)
        self.updated_at = current_datetime()

    def remove(self, removed_by: UUID) -> None:
        if self.is_deleted:
            return

        self.deleted_at = current_datetime()

        self.register_event(
            ProjectMemberRemoved(
                project_id=self.project_id,
                user_id=self.user_id,
                removed_by=removed_by,
            ),
        )


@dataclass(kw_only=True)
class ProjectStage(Entity):
    """
    Этап проекта - структурированный шаг в жизненном цикле проекта.
    """

    project_id: UUID
    name: str
    order: Annotated[int, Doc("Порядковый номер этапа")]

    status: ProjectStageStatus

    planned_start: Annotated[date | None, Doc("Плановая дата начала")] = None
    planned_end: Annotated[date | None, Doc("Плановая дата завершения")] = None

    started_at: Annotated[datetime | None, Doc("Фактическое время начала")] = None
    completed_at: Annotated[datetime | None, Doc("Фактическое время завершения")] = None
    responsible_id: Annotated[UUID | None, Doc("Ответственный за этап")] = None

    description: str | None = None
    completion_criteria: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Project stage name cannot be empty")

        if self.order < 1:
            raise ValueError(
                "Project stage order cannot be less then 1. "
                "Order should be: 1; 2; 3; 4; ..."
            )

        # Плановая дата начала не может быть больше плановой даты завершения
        if self.planned_start is not None and self.planned_end is not None \
                and self.planned_start > self.planned_end:
            raise InvariantViolationError(
                "Planned planned_start date cannot be greater than planned planned_end date"
            )

        # Проект не может завершиться раньше, чам он начнётся
        if self.started_at is not None and self.completed_at is not None \
                and self.started_at > self.completed_at:
            raise InvariantViolationError("The project cannot be completed before it starts")

    @property
    def is_overdue(self) -> bool:
        """
        Просрочен ли срок выполнения.
        """

        today = current_datetime().date()
        return bool(self.planned_end is not None and today > self.planned_end)

    @property
    def planned_duration_days(self) -> int | None:
        """
        Плановая продолжительность этапа в днях.
        """

        if self.planned_start is not None and self.planned_end is not None:
            return (self.planned_end - self.planned_start).days + 1

        return None

    def establish_planned_schedule(self, start: date, end: date) -> None:
        """
        Запланировать график проведения этапа.
        """

        if start > end:
            raise ValueError("Start planned date cannot be greater than planned planned_end date")

        # Нельзя сдвигать плановое начало этапа в прошлое, если этап уже начался
        if self.started_at is not None and start < self.started_at.date():
            raise InvariantViolationError("Cannot set planned end date before actual start date")

        self.planned_start = start
        self.planned_end = end
        self.updated_at = current_datetime()

    def edit(
            self,
            *,
            name: str | None = None,
            description: str | None = None,
            responsible_id: UUID | None = None,
            completion_criteria: list[str] | None = None,
    ) -> None:
        """
        Обновить справочную информацию этапа.
        """

        changed = False

        if name is not None and name.strip() and name.strip() != self.name:
            self.name = name.strip()
            changed = True

        if description is not None and description.strip() \
                and description.strip() != self.description:
            self.description = description.strip()
            changed = True

        if responsible_id is not None and responsible_id != self.responsible_id:
            self.responsible_id = responsible_id
            changed = True

        if completion_criteria is not None and completion_criteria != self.completion_criteria:
            self.completion_criteria = completion_criteria
            changed = True

        if changed:
            self.updated_at = current_datetime()

    def start(self) -> None:
        """
        Начать этап проекта.
        """

        if self.status != ProjectStageStatus.PLANNED:
            raise InvalidStateError("Only PLANNED stage can be started")

        self.status = ProjectStageStatus.ACTIVE
        self.started_at = current_datetime()
        self.updated_at = current_datetime()

    def complete(self) -> None:
        if self.status != ProjectStageStatus.ACTIVE:
            raise InvalidStateError("Only ACTIVE stage can be completed")

        self.status = ProjectStageStatus.COMPLETED
        self.completed_at = current_datetime()
        self.updated_at = current_datetime()

    def skip(self) -> None:
        """
        Пропустить запланированный этап (без выполнения).
        """

        if self.status in {ProjectStageStatus.COMPLETED, ProjectStageStatus.SKIPPED}:
            raise InvalidStateError(f"Cannot skip a stage with status {self.status}")

        self.status = ProjectStageStatus.SKIPPED
        self.updated_at = current_datetime()


@dataclass(kw_only=True)
class Project(AggregateRoot):
    """
    Проект - изолированный контейнер с процессами: тикеты, задачи, контекстные роли.
    """

    name: str
    key: ProjectKey
    description: str | None = None
    counterparty_id: UUID | None = None
    status: ProjectStatus

    owner_id: UUID
    created_by: UUID

    current_stage_id: UUID | None = None
    stages: list[ProjectStage] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Project name cannot be empty")

    @classmethod
    def create(
            cls,
            name: str,
            key: ProjectKey,
            created_by: UUID,
            description: str | None = None,
            counterparty_id: UUID | None = None,
    ) -> Self:
        stripped_name = name.strip()
        project = cls(
            name=stripped_name,
            key=key,
            description=description,
            counterparty_id=counterparty_id,
            owner_id=created_by,
            status=ProjectStatus.ACTIVE,
            created_by=created_by,
        )
        project.register_event(
            ProjectCreated(
                project_id=project.id,
                name=name,
                owner_id=project.owner_id,
                created_by=created_by,
                counterparty_id=counterparty_id,
            )
        )
        return project

    def create_member(
            self, user_id: UUID, project_roles: list[ProjectRole], created_by: UUID
    ) -> ProjectMember:
        """
        Создание участника в проекте (фабричный метод).
        """

        if self.status == ProjectStatus.ARCHIVED:
            raise InvalidStateError("Cannot add member in ARCHIVED project")

        unique_project_roles = set(project_roles)

        if len(unique_project_roles) > len(ProjectRole):
            raise InvariantViolationError("Too many project roles granted")

        member = ProjectMember(
            project_id=self.id,
            project_roles=list(project_roles),
            user_id=user_id,
            created_by=created_by,
        )

        self.register_event(
            ProjectMemberCreated(
                project_id=self.id,
                user_id=user_id,
                created_by=created_by,
            )
        )

        return member

    def archive(self, archived_by: UUID) -> None:
        """
        Архивирование проекта (мягкое удаление).
        """

        if self.is_deleted:
            return

        self.status = ProjectStatus.ARCHIVED
        self.deleted_at = current_datetime()

        self.register_event(
            ProjectArchived(project_id=self.id, archived_by=archived_by)
        )
