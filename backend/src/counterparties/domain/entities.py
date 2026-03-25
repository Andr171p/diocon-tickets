from dataclasses import dataclass
from uuid import UUID

from pydantic import EmailStr

from ...shared.domain.entities import Entity
from ...shared.domain.exceptions import InvariantViolationError
from .vo import ContactPerson, CounterpartyType, Inn, Kpp, Okpo, Phone

INDIVIDUAL_INN_LENGTH = 12
LEGAL_INN_LENGTH = 10


@dataclass(kw_only=True)
class Counterparty(Entity):
    """
    Контрагент - компания с которой ведётся работа (заказчик)
    """

    counterparty_type: CounterpartyType
    name: str
    legal_name: str
    inn: Inn
    kpp: Kpp | None = None
    okpo: Okpo | None = None
    phone: Phone
    email: EmailStr
    address: str | None = None
    avatar_url: str | None = None
    contact_person: ContactPerson | None = None
    is_active: bool = True

    # Поля для master-slave иерархии (удобно для филиалов)
    parent_id: UUID | None = None
    is_slave: bool = False

    def __post_init__(self) -> None:
        """Проверка инвариантов контрагента"""

        # 1. Проверка корректности длины ИНН в зависимости от типа контрагента
        inn_length = len(self.inn.value)
        match self.counterparty_type:
            case CounterpartyType.INDIVIDUAL | CounterpartyType.INDIVIDUAL_ENTREPRENEUR:
                if inn_length != INDIVIDUAL_INN_LENGTH:
                    raise InvariantViolationError(
                        "For an individual, the IIN must contain 12 digits "
                        f"(received {inn_length})"
                    )
            case CounterpartyType.LEGAL_ENTITY | CounterpartyType.BRANCH:
                if inn_length != LEGAL_INN_LENGTH:
                    raise InvariantViolationError(
                        "For a legal entity, the IIN must contain 10 digits "
                        f"(received {inn_length})"
                    )

        # 3. Проверка наличия КПП
        if self.counterparty_type in {CounterpartyType.LEGAL_ENTITY, CounterpartyType.BRANCH}:
            if self.kpp is None:
                raise InvariantViolationError(
                    f"For counterparty type '{self.counterparty_type.value}' KPP required"
                )
        elif self.kpp is not None:
            raise InvariantViolationError(
                f"For counterparty type {self.counterparty_type.value} KPP not required"
            )

        # 4. Инвариант: если контрагент дочерний, то нужна ссылка на головной
        if self.is_slave and self.parent_id is None:
            raise InvariantViolationError(
                "Slave counterparty (branch) must have a link to the parent ID (parent company)"
            )

        # 5. Инвариант: Master не может быть slave
        if self.parent_id is not None and self.is_slave is False:
            object.__setattr__(self, "is_slave", True)

    @property
    def is_master(self) -> bool:
        """Является ли контрагент основным"""

        return self.parent_id is None
