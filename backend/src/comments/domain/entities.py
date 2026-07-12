from typing import Self

from dataclasses import dataclass, field
from uuid import UUID

from src.media.domain.entities import Attachment
from src.shared.domain.entities import AggregateRoot, Entity
from src.shared.utils.time import current_datetime

from .events import CommentCreated, CommentEdited, ReactionCreated
from .vo import AggregateReference, AggregateType, CommentVisibility


@dataclass(kw_only=True)
class Reaction(Entity):
    """
    Реакция на комментарий, например: 👍.
    """

    comment_id: UUID
    author_id: UUID
    emoji: str

    @classmethod
    def create(cls, comment_id: UUID, author_id: UUID, emoji: str) -> Self:
        reaction = cls(comment_id=comment_id, author_id=author_id, emoji=emoji)
        reaction.register_event(
            ReactionCreated(
                comment_id=comment_id,
                author_id=author_id,
                emoji=emoji,
            )
        )
        return reaction

    def change(self, new_emoji: str) -> None:
        """Изменение реакции без создания новой сущности."""

        if self.emoji == new_emoji:
            return

        self.emoji = new_emoji
        self.updated_at = current_datetime()


@dataclass(kw_only=True)
class Comment(AggregateRoot):
    """
    Комментарий - один из способов обсуждения рабочих процессов.
    """

    aggregate: AggregateReference

    author_id: UUID
    text: str
    visibility: CommentVisibility = field(default=CommentVisibility.PUBLIC)

    attachments: list[Attachment] = field(default_factory=list)

    parent_comment_id: UUID | None = None
    reply_count: int = field(default=0)

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("Comment text cannot be empty")

    @property
    def is_reply(self) -> bool:
        return self.parent_comment_id is not None

    def _increment_reply_count(self) -> None:
        self.reply_count += 1

    def decrement_reply_count(self) -> None:
        if self.reply_count > 0:
            self.reply_count -= 1

    @classmethod
    def create(
            cls,
            aggregate_type: AggregateType,
            aggregate_id: UUID,
            author_id: UUID,
            text: str,
            visibility: CommentVisibility = CommentVisibility.PUBLIC,
    ) -> Self:
        if not text.strip():
            raise ValueError("Comment text cannot be empty")

        comment = cls(
            aggregate=AggregateReference(id=aggregate_id, type=aggregate_type),
            author_id=author_id,
            text=text,
            visibility=visibility,
        )

        is_public = visibility == CommentVisibility.PUBLIC
        comment.register_event(
            CommentCreated(
                comment_id=comment.id,
                aggregate_type=aggregate_type,
                aggregate_id=aggregate_id,
                author_id=author_id,
                is_public=is_public,
            )
        )
        return comment

    def create_reply(
            self,
            author_id: UUID,
            text: str,
            visibility: CommentVisibility = CommentVisibility.PUBLIC,
    ) -> Self:
        """Ответить на комментарий."""

        if not text.strip():
            raise ValueError("Comment text cannot be empty")

        reply = Comment(
            aggregate=AggregateReference(id=self.aggregate.id, type=self.aggregate.type),
            author_id=author_id,
            text=text.strip(),
            visibility=visibility,
            parent_comment_id=self.id,
        )
        self._increment_reply_count()

        is_public = visibility == CommentVisibility.PUBLIC
        reply.register_event(
            CommentCreated(
                comment_id=reply.id,
                parent_comment_id=self.id,
                aggregate_type=self.aggregate.type,
                aggregate_id=self.aggregate.id,
                author_id=author_id,
                is_public=is_public,
            )
        )

        return reply

    def edit(self, new_text: str, edited_by: UUID) -> None:
        """Отредактировать комментарий."""

        if not new_text.strip():
            raise ValueError("Comment text cannot be empty")

        if self.text == new_text.strip():
            return

        self.text = new_text.strip()
        self.updated_at = current_datetime()

        self.register_event(
            CommentEdited(
                comment_id=self.id,
                aggregate_type=self.aggregate.type,
                aggregate_id=self.aggregate.id,
                edited_by=edited_by,
            )
        )

    def remove(self) -> None:
        if self.is_deleted:
            return

        self.deleted_at = current_datetime()
