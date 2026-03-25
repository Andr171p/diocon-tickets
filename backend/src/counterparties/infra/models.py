from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from ...iam.infra.models import UserOrm

from uuid import UUID

from sqlalchemy import Enum, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...core.database import Base
from ..domain.vo import CounterpartyType


class CounterpartyOrm(Base):
    __tablename__ = "counterparties"

    counterparty_type: Mapped[CounterpartyType] = mapped_column(Enum(CounterpartyType))
    name: Mapped[str]
    legal_name: Mapped[str]
    inn: Mapped[str] = mapped_column(unique=True)
    kpp: Mapped[str | None] = mapped_column(nullable=True)
    okpo: Mapped[str | None] = mapped_column(nullable=True)
    phone: Mapped[str]
    email: Mapped[str] = mapped_column(unique=True)
    address: Mapped[str | None] = mapped_column(nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(nullable=True)
    contact_person: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    is_active: Mapped[bool]

    parent_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("counterparties.id"), nullable=True, unique=False
    )
    is_slave: Mapped[bool]

    parent: Mapped[Optional["CounterpartyOrm"]] = relationship(
        remote_side="CounterpartyOrm.id", back_populates="slaves",
    )
    slaves: Mapped[list["CounterpartyOrm"]] = relationship(
        back_populates="parent", cascade="all, delete-orphan"
    )

    customers: Mapped[list["UserOrm"]] = relationship(back_populates="counterparty")
