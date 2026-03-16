from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base


class RefreshTokenOrm(Base):
    __tablename__ = "refresh_token"

    user_id: Mapped[UUID]
    token: Mapped[str] = mapped_column(unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked: Mapped[bool]
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
