from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Enum
from sqlalchemy.orm import Mapped, mapped_column

from ...core.entities import UserRole
from ..base import Base


class InvitationOrm(Base):
    __tablename__ = "invitations"

    email: Mapped[str]
    token: Mapped[str] = mapped_column(unique=True)
    created_by: Mapped[UUID]
    intended_role: Mapped[UserRole] = mapped_column(Enum(UserRole))
    counterparty_id: Mapped[UUID | None] = mapped_column(nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    is_used: Mapped[bool]
