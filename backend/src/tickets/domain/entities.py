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
from .events import TicketCreated
from .vo import CommentType, Tag, TicketNumber, TicketPriority, TicketStatus

COMMENT_TYPE_DISPLAY_NAMES: dict[CommentType, str] = {
    CommentType.INTERNAL: "внутренний",
    CommentType.PUBLIC: "публичный",
    CommentType.NOTE: "личный (заметка)"
}


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

    counterparty_id: UUID | None = None
    created_by_role: UserRole
    created_by: UUID
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
            created_by_role: UserRole,
            created_by: UUID,
            title: str,
            description: str,
            priority: TicketPriority,
            counterparty_name: str | None = None,
            counterparty_id: UUID | None = None,
            tags: list[Tag] | None = None,
    ) -> Self:
        """Создание тикета"""

        # 1. Генерация уникального ID и создание номера
        ticket_id = uuid4()
        ticket_number = TicketNumber.create(ticket_id, counterparty_name)

        # 2. Создание доменной сущности
        ticket = cls(
            id=ticket_id,
            created_by_role=created_by_role,
            created_by=created_by,
            number=ticket_number,
            title=title,
            description=description,
            priority=priority,
            status=TicketStatus.NEW,
            counterparty_id=counterparty_id,
            tags=tags if tags is not None else [],
            history=[
                TicketHistoryEntry(
                    ticket_id=ticket_id,
                    actor_id=created_by,
                    action="ticket_created",
                    description=f"Создан тикет с номером - {ticket_number}"
                )
            ]
        )

        # 3. Регистрация доменного события
        ticket.register_event(
            TicketCreated(
                ticket_id=ticket_id,
                title=title,
                created_by=created_by,
                priority=priority,
                counterparty_id=counterparty_id,
            )
        )
        return ticket

    def assign_to(self, assignee_id: UUID, assigned_by: UUID, assigned_by_role: UserRole) -> None:
        """Назначает тикет на исполнителя"""

        if assigned_by_role not in {
            UserRole.SUPPORT_AGENT, UserRole.SUPPORT_MANAGER, UserRole.ADMIN
        }:
            raise PermissionDeniedError("Only support staff can assign tickets")

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

        if changed_by_role not in {
            UserRole.EXECUTOR, UserRole.SUPPORT_AGENT, UserRole.SUPPORT_MANAGER, UserRole.ADMIN
        }:
            raise PermissionDeniedError("You don't have permission to change status")

        old_status = self.status
        self.status = new_status

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
