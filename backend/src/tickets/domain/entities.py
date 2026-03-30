from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from ...iam.domain.exceptions import PermissionDeniedError
from ...iam.domain.vo import UserRole
from ...media.domain.entities import Attachment
from ...shared.domain.entities import AggregateRoot, Entity
from ...shared.utils.time import current_datetime
from .vo import CommentType, Tag, TicketPriority, TicketStatus


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
class Ticket(AggregateRoot):
    """
    Агрегат Тикет — центральная сущность системы
    """

    counterparty_id: UUID
    created_by: UUID
    title: str
    description: str
    status: TicketStatus
    priority: TicketPriority
    assigned_to: UUID
    closed_at: datetime | None = None

    # Дополнительно
    tags: list[Tag] = field(default_factory=list)

    # Внутренние коллекции агрегата
    comments: list[Comment] = field(default_factory=list)
    attachments: list[Attachment] = field(default_factory=list)
    history: list[...]
