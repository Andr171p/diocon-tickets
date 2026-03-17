from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .counterparty import CounterpartyOrm

from uuid import UUID

from sqlalchemy import Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...core.entities import UserRole
from ..base import Base


class UserOrm(Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(unique=True)
    username: Mapped[str | None] = mapped_column(nullable=True)
    full_name: Mapped[str | None] = mapped_column(nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(nullable=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole))
    counterparty_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("counterparties.id"), nullable=True, unique=False,
    )
    password_hash: Mapped[str] = mapped_column(unique=True)
    is_active: Mapped[bool]

    counterparty: Mapped[Optional["CounterpartyOrm"]] = relationship(back_populates="customers")
