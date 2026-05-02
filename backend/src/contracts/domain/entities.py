from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from uuid import UUID

from ...shared.domain.entities import AggregateRoot
from .vo import NonNegativeDecimal


@dataclass(kw_only=True)
class ServiceContract(AggregateRoot):
    """
    Сервисный договор с контрагентом
    """

    contract_number: ...
    counterparty_id: UUID
    start_date: date
    end_date: date | None = None

    # Всего оплачено часов
    total_hours: NonNegativeDecimal
    # Часов уже потрачено
    consumed_hours: NonNegativeDecimal = field(default=NonNegativeDecimal(Decimal(0)))
    # Оставшиеся часы
    remaining_hours: NonNegativeDecimal = field(init=False)

    status: ...
    contract_type: ...

    # Пакеты часов (может быть несколько)
    packages: list[...] = field(default_factory=list)

    created_by: UUID
