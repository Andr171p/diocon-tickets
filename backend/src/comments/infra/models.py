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
        Index("ix_comments_aggregate", "aggregate_type", "aggregate_id", "created_at"),
        Index("ix_comments_author", "author_id", "created_at"),
        # Частичный индекс для ускорения `WHERE parent_comment_id IS NULL`
        Index(
            "ix_comments_root_null",
            "aggregate_type",
            "aggregate_id",
            "created_at",
            postgresql_where=(parent_comment_id.is_(None)),
        ),
        Index(
            "ix_comments_aggregate_visibility",
            "aggregate_type",
            "aggregate_id",
            "visibility",
            "created_at",
        ),
    )


class ReactionOrm(Base):
    __tablename__ = "reactions"

    comment_id: Mapped[UUID] = mapped_column(ForeignKey("comments.id"), unique=False)
    author_id: Mapped[UUID]
    emoji: Mapped[str]

    comment: Mapped["CommentOrm"] = relationship(back_populates="reactions")

    __table_args__ = (
        UniqueConstraint("comment_id", "author_id", "emoji", name="uq_comment_reaction"),
        Index("ix_reactions_comment_emoji", "comment_id", "emoji"),
        Index("ix_reactions_author", "author_id", "created_at"),
    )
