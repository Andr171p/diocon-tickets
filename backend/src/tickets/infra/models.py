from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.media.infra.models import AttachmentOrm

from datetime import datetime
from uuid import UUID

from sqlalchemy import TEXT, Computed, DateTime, Enum, Index, String
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base
from src.shared.domain.vo import Priority

from ..domain.vo import TicketStatus, TicketType


class TicketOrm(Base):
    __tablename__ = "tickets"

    project_id: Mapped[UUID | None] = mapped_column(nullable=True)
    counterparty_id: Mapped[UUID | None] = mapped_column(nullable=True)
    product_id: Mapped[UUID | None] = mapped_column(nullable=True)

    created_by: Mapped[UUID]
    approved_by: Mapped[UUID | None] = mapped_column(nullable=True)
    resolved_by: Mapped[UUID | None] = mapped_column(nullable=True)
    closed_by: Mapped[UUID | None] = mapped_column(nullable=True)

    reporter_id: Mapped[UUID]
    assignee_id: Mapped[UUID | None] = mapped_column(nullable=True)

    number: Mapped[str] = mapped_column(String(25), unique=True)
    title: Mapped[str]
    description: Mapped[str] = mapped_column(TEXT)
    ticket_type: Mapped[TicketType] = mapped_column(Enum(TicketType))
    status: Mapped[TicketStatus] = mapped_column(Enum(TicketStatus))
    priority: Mapped[Priority] = mapped_column(Enum(Priority))

    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    tags: Mapped[list[dict[str, str]]] = mapped_column(JSONB)

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
