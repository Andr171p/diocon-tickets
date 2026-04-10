from typing import Self

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from ...iam.domain.exceptions import PermissionDeniedError
from ...iam.domain.vo import UserRole
from ...media.domain.entities import Attachment
from ...shared.domain.entities import AggregateRoot, Entity
from ...shared.domain.exceptions import InvariantViolationError
from ...shared.utils.time import current_datetime
from .constants import ALLOWED_ASSIGN_STATUSES, ALLOWED_TRANSITIONS, COMMENT_TYPE_DISPLAY_NAMES
from .events import ProjectCreated, TicketCreated
from .vo import (
    CommentType,
    ProjectKey,
    ProjectRole,
    ProjectStatus,
    Tag,
    TicketNumber,
    TicketPriority,
    TicketStatus,
)


@dataclass(kw_only=True)
class Comment(Entity):
    """
    Комментарий лоя тикета
    """

    ticket_id: UUID
    author_id: UUID
    author_role: UserRole
    text: str
    type: CommentType = field(default=CommentType.PUBLIC)
    attachments: list[Attachment] = field(default_factory=list)

    def edit(self, new_text: str, edited_by: UUID) -> None:
        """Редактирование комментария"""

        if edited_by != self.author_id:
            raise PermissionDeniedError("Only author can edit comment")

        self.text = new_text
        self.updated_at = current_datetime()


@dataclass(kw_only=True)
class TicketHistoryEntry(Entity):
    """
    Запись в истории изменения тикета.
    Всегда заполняется автоматически внутри бизнес-методов.
    """

    ticket_id: UUID
    actor_id: UUID  # Кто совершил действие
    action: str  # 'status_changed', 'assigned', 'comment_added'
    old_value: str | None = None
    new_value: str | None = None
    description: str = field(default="")  # Человеко-читаемое описание


@dataclass(kw_only=True)
class Ticket(AggregateRoot):
    """
    Агрегат Тикет — центральная сущность системы
    """

    project_id: UUID | None = None
    counterparty_id: UUID | None = None

    # Ключевые поля
    created_by: UUID  # Технический создатель
    created_by_role: UserRole
    reporter_id: UUID  # Инициатор/автор проблемы (тот кто пожаловался)

    number: TicketNumber
    title: str
    description: str
    status: TicketStatus
    priority: TicketPriority
    assigned_to: UUID | None = None
    closed_at: datetime | None = None

    # Дополнительно
    tags: list[Tag] = field(default_factory=list)

    # Внутренние коллекции агрегата
    comments: list[Comment] = field(default_factory=list)
    attachments: list[Attachment] = field(default_factory=list)
    history: list[TicketHistoryEntry] = field(default_factory=list)

    def __post_init__(self) -> None:
        # 1. Заголовок не должен быть пустым
        if not self.title.strip():
            raise ValueError("Title cannot be empty")

        # 2. если тикет создан клиентом - контрагент должен быть заполнен
        if self.created_by_role.is_customer() and self.counterparty_id is None:
            raise InvariantViolationError(
                "Customer-created ticket must be linked to a counterparty"
            )

    @classmethod
    def create(
        cls,
        ticket_number: TicketNumber,
        reporter_id: UUID,
        created_by: UUID,
        created_by_role: UserRole,
        title: str,
        description: str | None = None,
        priority: TicketPriority = TicketPriority.MEDIUM,
        project_id: UUID | None = None,
        counterparty_id: UUID | None = None,
        tags: list[Tag] | None = None,
    ) -> Self:
        """Создание тикета"""

        # 1. Создание доменной сущности
        ticket_id = uuid4()
        ticket = cls(
            id=ticket_id,
            created_by_role=created_by_role,
            created_by=created_by,
            reporter_id=reporter_id,
            number=ticket_number,
            title=title,
            description=description,
            priority=priority,
            status=TicketStatus.NEW,
            project_id=project_id,
            counterparty_id=counterparty_id,
            tags=tags if tags is not None else [],
            history=[
                TicketHistoryEntry(
                    ticket_id=ticket_id,
                    actor_id=created_by,
                    action="ticket_created",
                    description=f"Создан тикет с номером - {ticket_number}",
                )
            ],
        )

        # 2. Регистрация доменного события
        ticket.register_event(
            TicketCreated(
                ticket_id=ticket_id,
                title=title,
                created_by=created_by,
                reporter_id=reporter_id,
                priority=priority,
                counterparty_id=counterparty_id,
            )
        )

        return ticket

    def assign_to(self, assignee_id: UUID, assigned_by: UUID, assigned_by_role: UserRole) -> None:
        """Назначает тикет на исполнителя"""

        # 1. Назначить тикет могут только внутренние сотрудники
        if assigned_by_role not in {
            UserRole.SUPPORT_AGENT, UserRole.SUPPORT_MANAGER, UserRole.ADMIN
        }:
            raise PermissionDeniedError("Only support staff can assign tickets")

        # 2. Для назначения тикета должен быть определённый статус
        if self.status not in ALLOWED_ASSIGN_STATUSES:
            raise PermissionDeniedError(
                f"Cannot assign ticket in status '{self.status.value}'. "
                f"Allowed statuses: {', '.join(status for status in ALLOWED_ASSIGN_STATUSES)}"
            )

        # 3. Назначение исполнителя
        old_assignee = self.assigned_to
        self.assigned_to = assignee_id

        self.history.append(
            TicketHistoryEntry(
                ticket_id=self.id,
                actor_id=assigned_by,
                action="assigned",
                old_value=f"{old_assignee}" if old_assignee else None,
                new_value=f"{assignee_id}",
                description="Тикет назначен пользователю",
            )
        )

    def change_status(
            self, new_status: TicketStatus, changed_by: UUID, changed_by_role: UserRole
    ) -> None:
        """Изменение статуса"""

        # 1. Проверка возможности перехода к новому статусу
        if new_status in ALLOWED_TRANSITIONS.get(self.status, []):
            raise PermissionDeniedError(
                f"Not allowed status transition from '{self.status}' to '{new_status}'"
            )

        # 2. Есть ли права на изменение статуса
        if changed_by_role not in {
            UserRole.EXECUTOR, UserRole.SUPPORT_AGENT, UserRole.SUPPORT_MANAGER, UserRole.ADMIN
        }:
            raise PermissionDeniedError("You don't have permission to change status")

        # 3. Установка нового статуса
        old_status = self.status
        self.status = new_status

        # 4. Если тикет закрыт, то устанавливается время закрытия
        if new_status == TicketStatus.CLOSED:
            self.closed_at = current_datetime()

        self.history.append(
            TicketHistoryEntry(
                ticket_id=self.id,
                actor_id=changed_by,
                action="status_changed",
                old_value=f"{old_status}",
                new_value=f"{new_status}",
                description=(
                    f"Статус тикета изменён с `{old_status.value}` "
                    f"на `{new_status.value}`"
                )
            )
        )

    def add_comment(
            self,
            author_id: UUID,
            author_role: UserRole,
            text: str,
            comment_type: CommentType,
            attachments: list[Attachment] | None = None,
    ) -> None:
        """Добавление комментария"""

        self.comments.append(
            Comment(
                ticket_id=self.id,
                author_id=author_id,
                author_role=author_role,
                text=text,
                type=comment_type,
                attachments=attachments,
            )
        )

        self.history.append(
            TicketHistoryEntry(
                ticket_id=self.id,
                actor_id=author_id,
                action="comment_added",
                description=f"Добавлен {COMMENT_TYPE_DISPLAY_NAMES[comment_type]} комментарий"
            )
        )


@dataclass(kw_only=True)
class Membership(Entity):
    """
    Участник проекта
    """

    project_id: UUID
    user_id: UUID
    project_role: ProjectRole
    added_at: datetime = field(default_factory=current_datetime)
    added_by: UUID
    removed_at: datetime | None = None

    @property
    def is_active(self) -> bool:
        return self.removed_at is None


@dataclass(kw_only=True)
class Project(AggregateRoot):
    """
    Проект - контейнер для тикетов
    """

    name: str
    key: ProjectKey  # Короткий уникальный ключ
    description: str | None = None
    counterparty_id: UUID | None = None
    status: ProjectStatus
    # Владелец проекта, руководитель или ответственный
    owner_id: UUID
    # Участники проекта (члены команды)
    memberships: list[Membership] = field(default_factory=list)
    # Метаданные
    created_by: UUID

    def __post_init__(self) -> None:
        # 1. Наименование проекта не может быть пустым
        if not self.name.strip():
            raise ValueError("Project name cannot be empty")

        # 2. Владелец проекта должен быть среди его участников
        if not any(membership.user_id == self.owner_id for membership in self.memberships):
            raise InvariantViolationError("Owner must be a participant of the project")

    @classmethod
    def create(
            cls,
            name: str,
            key: str,
            owner_id: UUID,
            created_by: UUID,
            description: str | None = None,
            counterparty_id: UUID | None = None,
    ) -> Self:
        """Создание проекта"""

        project_id = uuid4()
        owner = Membership(
            project_id=project_id,
            user_id=owner_id,
            project_role=ProjectRole.OWNER,
            added_by=created_by,
        )
        project = cls(
            id=project_id,
            name=name,
            key=ProjectKey(key),
            description=description,
            counterparty_id=counterparty_id,
            owner_id=owner_id,
            status=ProjectStatus.ACTIVE,
            memberships=[owner],
            created_by=created_by,
        )
        project.register_event(
            ProjectCreated(
                project_id=project_id,
                name=name,
                created_by=created_by,
                counterparty_id=counterparty_id,
            )
        )
        return project

    def add_member(
            self,
            user_id: UUID,
            project_role: ProjectRole,
            added_by: UUID,
            added_by_role: UserRole,
    ) -> None:
        """Добавление участника"""

        # 1. Проверка прав на добавление
        if added_by != self.owner_id and added_by_role not in {
            UserRole.SUPPORT_MANAGER, UserRole.SUPPORT_AGENT, UserRole.ADMIN,
        }:
            raise PermissionDeniedError("Only owner or support stuff can add participants")

        # 2. Проверка того, что участник уже есть
        if user_id in [membership.user_id for membership in self.memberships]:
            raise InvariantViolationError(f"User with ID {user_id} is already a participant")

        self.memberships.append(
            Membership(
                project_id=self.id,
                user_id=user_id,
                project_role=project_role,
                added_by=added_by,
            )
        )
