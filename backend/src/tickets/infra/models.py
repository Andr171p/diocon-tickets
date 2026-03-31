from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...media.infra.models import AttachmentOrm

from datetime import datetime
from uuid import UUID

from sqlalchemy import TEXT, DateTime, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...core.database import Base
from ...iam.domain.vo import UserRole
from ..domain.vo import CommentType, TicketPriority, TicketStatus


class TicketOrm(Base):
    __tablename__ = "tickets"

    counterparty_id: Mapped[UUID | None] = mapped_column(nullable=True)
    created_by_role: Mapped[UserRole] = mapped_column(Enum(UserRole))
    created_by: Mapped[UUID]
    title: Mapped[str]
    description: Mapped[str] = mapped_column(TEXT)
    status: Mapped[TicketStatus] = mapped_column(Enum(TicketStatus))
    priority: TicketPriority = mapped_column(Enum(TicketPriority))
    assigned_to: Mapped[UUID | None] = mapped_column(nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    tags: Mapped[list[dict[str, str]]] = mapped_column(JSONB)

    comments: Mapped[list["CommentOrm"]] = relationship(back_populates="ticket")
    history: Mapped[list["TicketHistoryEntryOrm"]] = relationship(back_populates="ticket")
    attachments: Mapped[list["AttachmentOrm"]] = relationship(
        primaryjoin=(
            "and_(AttachmentOrm.owner_type=='ticket', "
            "foreign(AttachmentOrm.owner_id)==TicketOrm.id"
        ),
        viewonly=True,
    )


class CommentOrm(Base):
    __tablename__ = "comments"

    ticket_id: Mapped[UUID] = mapped_column(ForeignKey("tickets.id"), unique=False)
    author_id: Mapped[UUID]
    author_role: Mapped[UserRole] = mapped_column(Enum(UserRole))
    text: Mapped[str] = mapped_column(TEXT)
    type: Mapped[CommentType] = mapped_column(Enum(CommentType))

    ticket: Mapped["TicketOrm"] = relationship(back_populates="comments")
    attachments: Mapped[list["AttachmentOrm"]] = relationship(
        primaryjoin=(
            "and_(AttachmentOrm.owner_type=='comment', "
            "foreign(AttachmentOrm.owner_id)==CommentOrm.id"
        ),
        viewonly=True,
    )


class TicketHistoryEntryOrm(Base):
    __tablename__ = "ticket_history_entries"

    ticket_id: Mapped[UUID] = mapped_column(ForeignKey("tickets.id"), unique=False)
    actor_id: Mapped[UUID]
    action: Mapped[str]
    old_value: Mapped[str | None] = mapped_column(nullable=True)
    new_value: Mapped[str | None] = mapped_column(nullable=True)
    description: Mapped[str] = mapped_column(TEXT)

    ticket: Mapped["TicketOrm"] = relationship(back_populates="history")
