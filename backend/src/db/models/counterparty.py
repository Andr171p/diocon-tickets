from uuid import UUID

from sqlalchemy import Enum, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...core.entities import CounterpartyType
from ..base import Base


class CounterpartyOrm(Base):
    __tablename__ = "counterparties"

    counterparty_type: Mapped[CounterpartyType] = mapped_column(Enum(CounterpartyType))
    name: Mapped[str]
    legal_name: Mapped[str]
    inn: Mapped[str | None] = mapped_column(nullable=True, unique=True)
    kpp: Mapped[str]
    okpo: Mapped[str | None] = mapped_column(nullable=True)
    phone: Mapped[str]
    email: Mapped[str]
    address: Mapped[str | None] = mapped_column(nullable=True)
    is_active: Mapped[bool]

    contact_person: Mapped["ContactPersonOrm"] = relationship(back_populates="counterparty")


class ContactPersonOrm(Base):
    __tablename__ = "contact_persons"

    counterparty_id: Mapped[UUID] = mapped_column(ForeignKey("counterparties.id"), unique=True)

    first_name: Mapped[str | None] = mapped_column(nullable=True)
    last_name: Mapped[str | None] = mapped_column(nullable=True)
    middle_name: Mapped[str | None] = mapped_column(nullable=True)
    phone: Mapped[str]
    email: Mapped[str]
    messengers: Mapped[dict[str, str]] = mapped_column(JSONB)

    counterparty: Mapped["CounterpartyOrm"] = relationship(back_populates="contact_person")
