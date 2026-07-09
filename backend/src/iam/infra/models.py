from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base

from ..domain.vo import UserRole


class UserOrm(Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(unique=True)
    username: Mapped[str | None] = mapped_column(nullable=True)
    full_name: Mapped[str | None] = mapped_column(nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(nullable=True)
    roles: Mapped[list[UserRole]] = mapped_column(JSONB)
    counterparty_id: Mapped[UUID | None] = mapped_column(nullable=True)
    password_hash: Mapped[str] = mapped_column(unique=True)
    is_active: Mapped[bool]

    __table_args__ = (
        Index("ix_users_counterparty_id", "counterparty_id"),
        Index("ix_users_is_active", "is_active"),
        Index("ix_users_roles_gin", "roles", postgresql_using="gin"),
    )


class InvitationOrm(Base):
    __tablename__ = "invitations"

    email: Mapped[str]
    token: Mapped[str] = mapped_column(unique=True)
    invited_by: Mapped[UUID]
    granted_roles: Mapped[list[UserRole]] = mapped_column(JSONB)
    counterparty_id: Mapped[UUID | None] = mapped_column(nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_used: Mapped[bool]

    __table_args__ = (
        Index("ix_invitation_email", "email"),
        Index("ix_invitation_expires_at", "expires_at"),
        Index("ix_invitation_roles_gin", "granted_roles", postgresql_using="gin"),
    )
