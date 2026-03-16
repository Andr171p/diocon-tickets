from sqlalchemy import Enum
from sqlalchemy.orm import Mapped, mapped_column

from ...core.entities import UserRole
from ..base import Base


class UserOrm(Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(unique=True)
    username: Mapped[str | None] = mapped_column(nullable=True)
    full_name: Mapped[str | None] = mapped_column(nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(nullable=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole))
    password_hash: Mapped[str] = mapped_column(unique=True)
    is_active: Mapped[bool]
