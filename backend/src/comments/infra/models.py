from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.media.infra.models import AttachmentOrm

from uuid import UUID

from sqlalchemy import TEXT, Enum, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base

from ..domain.vo import AggregateType, CommentVisibility


class CommentOrm(Base):
    __tablename__ = "comments"

    aggregate_type: Mapped[AggregateType] = mapped_column(Enum(AggregateType))
    aggregate_id: Mapped[UUID]

    author_id: Mapped[UUID]
    text: Mapped[str] = mapped_column(TEXT)
    visibility: Mapped[CommentVisibility] = mapped_column(Enum(CommentVisibility))

    reply_count: Mapped[int] = mapped_column(default=0)
    parent_comment_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("comments.id"), nullable=True
    )

    parent_comment: Mapped["CommentOrm | None"] = relationship(
        remote_side="CommentOrm.id", back_populates="replies", lazy="selectin",
    )
    replies: Mapped[list["CommentOrm"]] = relationship(
        back_populates="parent_comment", lazy="selectin"
    )
    attachments: Mapped[list["AttachmentOrm"]] = relationship(
        primaryjoin=(
            "and_(AttachmentOrm.owner_type=='comment', "
            "foreign(AttachmentOrm.owner_id)==CommentOrm.id)"
        ),
        viewonly=True,
        lazy="selectin",
    )
    reactions: Mapped[list["ReactionOrm"]] = relationship(back_populates="comment")

    __table_args__ = (
        Index("ix_comments_ticket_id", "ticket_id"),
        Index("ix_comments_parent_comment_id", "parent_comment_id"),
    )


class ReactionOrm(Base):
    __tablename__ = "reactions"

    comment_id: Mapped[UUID] = mapped_column(ForeignKey("comments.id"), unique=False)
    author_id: Mapped[UUID]
    emoji: Mapped[str]

    comment: Mapped["CommentOrm"] = relationship(back_populates="reactions")

    __table_args__ = (
        UniqueConstraint(
            "comment_id", "author_id", "emoji", name="uq_comment_reaction"
        ),
        Index("ix_reactions_comment_author", "comment_id", "author_id"),
    )
