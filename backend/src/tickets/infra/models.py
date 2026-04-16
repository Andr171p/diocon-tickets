from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...media.infra.models import AttachmentOrm

from datetime import datetime
from uuid import UUID

from sqlalchemy import TEXT, Computed, DateTime, Enum, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...core.database import Base
from ...iam.domain.vo import UserRole
from ..domain.vo import CommentType, ProjectRole, ProjectStatus, TicketPriority, TicketStatus


class TicketOrm(Base):
    __tablename__ = "tickets"

    project_id: Mapped[UUID | None] = mapped_column(ForeignKey("projects.id"), nullable=True)
    counterparty_id: Mapped[UUID | None] = mapped_column(nullable=True)
    created_by_role: Mapped[UserRole] = mapped_column(Enum(UserRole))
    created_by: Mapped[UUID]
    reporter_id: Mapped[UUID]
    number: Mapped[str] = mapped_column(String(25), unique=True)
    title: Mapped[str]
    description: Mapped[str] = mapped_column(TEXT)
    status: Mapped[TicketStatus] = mapped_column(Enum(TicketStatus))
    priority: Mapped[TicketPriority] = mapped_column(Enum(TicketPriority))
    assigned_to: Mapped[UUID | None] = mapped_column(nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    tags: Mapped[list[dict[str, str]]] = mapped_column(JSONB)

    comments: Mapped[list["CommentOrm"]] = relationship(back_populates="ticket")
    history: Mapped[list["TicketHistoryEntryOrm"]] = relationship(back_populates="ticket")
    attachments: Mapped[list["AttachmentOrm"]] = relationship(
        primaryjoin=(
            "and_(AttachmentOrm.owner_type=='ticket', "
            "foreign(AttachmentOrm.owner_id)==TicketOrm.id)"
        ),
        viewonly=True,
    )

    search_vector: Mapped[str] = mapped_column(
        TSVECTOR,
        Computed(
            "to_tsvector('russian', coalesce(title, '') || ' ' || coalesce(description, ''))",
            persisted=True,
        ),
        nullable=True,
    )
    __table_args__ = (
        Index("ix_tickets_search_vector", "search_vector", postgresql_using="gin"),
    )


class CommentOrm(Base):
    __tablename__ = "comments"

    ticket_id: Mapped[UUID] = mapped_column(ForeignKey("tickets.id"), unique=False)
    author_id: Mapped[UUID]
    author_role: Mapped[UserRole] = mapped_column(Enum(UserRole))
    text: Mapped[str] = mapped_column(TEXT)
    comment_type: Mapped[CommentType] = mapped_column(Enum(CommentType))

    ticket: Mapped["TicketOrm"] = relationship(back_populates="comments")
    attachments: Mapped[list["AttachmentOrm"]] = relationship(
        primaryjoin=(
            "and_(AttachmentOrm.owner_type=='comment', "
            "foreign(AttachmentOrm.owner_id)==CommentOrm.id)"
        ),
        viewonly=True,
        lazy="selectin",
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


class MembershipOrm(Base):
    __tablename__ = "project_memberships"

    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id"), unique=False)
    user_id: Mapped[UUID]
    project_role: Mapped[ProjectRole] = mapped_column(Enum(ProjectRole))
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    added_by: Mapped[UUID]
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    project: Mapped["ProjectOrm"] = relationship(back_populates="memberships")


class ProjectOrm(Base):
    __tablename__ = "projects"

    name: Mapped[str]
    key: Mapped[str] = mapped_column(unique=True)
    description: Mapped[str | None] = mapped_column(nullable=True)
    counterparty_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("counterparties.id"), nullable=True
    )
    status: Mapped[ProjectStatus] = mapped_column(Enum(ProjectStatus))
    owner_id: Mapped[UUID]
    memberships: Mapped[list["MembershipOrm"]] = relationship(
        back_populates="project", lazy="selectin"
    )
    created_by: Mapped[UUID]
