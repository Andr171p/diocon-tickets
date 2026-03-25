from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ..shared.domain.exceptions import AlreadyExistsError, NotFoundError
from .domain.entities import Counterparty
from .domain.repo import CounterpartyRepository
from .domain.vo import ContactPerson, Inn, Kpp, Okpo, Phone
from .mappers import map_counterparty_to_response
from .schemas import CounterpartyCreate, CounterpartyResponse


class CounterpartyService:
    def __init__(self, session: AsyncSession, repository: CounterpartyRepository) -> None:
        self.session = session
        self.repository = repository

    async def create(self, data: CounterpartyCreate) -> CounterpartyResponse:
        """Создание нового контрагента (по умолчанию головной)"""

        # 1. Проверка на уникальность (ИНН + email)
        exists_counterparty = await self.repository.get_by_inn(Inn(data.inn))
        if exists_counterparty is not None:
            raise AlreadyExistsError(f"Counterparty with INN {data.inn} already exists")
        exists_counterparty = await self.repository.get_by_email(data.email)
        if exists_counterparty is not None:
            raise AlreadyExistsError(f"This {data.email} email address already used")

        # 2. Создание доменных примитивов и объектов значений
        inn = Inn(data.inn)
        kpp = None if data.kpp is None else Kpp(data.kpp)
        okpo = None if data.okpo is None else Okpo(data.okpo)
        phone = Phone(data.phone)

        # 3. Формирование контактного лица
        contact_person = (
            None
            if data.contact_person is None
            else ContactPerson.create(
                first_name=data.contact_person.first_name,
                last_name=data.contact_person.last_name,
                middle_name=data.contact_person.middle_name,
                phone=data.contact_person.phone,
                email=data.contact_person.email,
                messengers=data.contact_person.messengers,
            )
        )

        # 4. Создание доменной сущности
        counterparty = Counterparty(
            counterparty_type=data.counterparty_type,
            name=data.name,
            legal_name=data.legal_name,
            inn=inn,
            kpp=kpp,
            okpo=okpo,
            phone=phone,
            email=data.email,
            address=data.address,
            contact_person=contact_person,
        )

        # 5. Запись в базу данных
        await self.repository.create(counterparty)
        await self.session.commit()

        return map_counterparty_to_response(counterparty)

    async def add_branch(self, parent_id: UUID, data: CounterpartyCreate) -> CounterpartyResponse:
        """
        Добавление дочернего контрагента (например другой филиал)
        """

        # 1. Проверка на существование
        exists_counterparty = await self.repository.read(parent_id)
        if exists_counterparty is None:
            raise NotFoundError(f"Parent counterparty with ID {parent_id} not found")

        # 2. Создание доменных примитивов и объектов значений
        inn = Inn(data.inn)
        kpp = None if data.kpp is None else Kpp(data.kpp)
        okpo = None if data.okpo is None else Okpo(data.okpo)
        phone = Phone(data.phone)

        # 3. Формирование контактного лица
        contact_person = (
            None
            if data.contact_person is None
            else ContactPerson.create(
                first_name=data.contact_person.first_name,
                last_name=data.contact_person.last_name,
                middle_name=data.contact_person.middle_name,
                phone=data.contact_person.phone,
                email=data.contact_person.email,
                messengers=data.contact_person.messengers,
            )
        )

        # 4. Создание доменной сущности
        counterparty = Counterparty(
            counterparty_type=data.counterparty_type,
            name=data.name,
            legal_name=data.legal_name,
            inn=inn,
            kpp=kpp,
            okpo=okpo,
            phone=phone,
            email=data.email,
            address=data.address,
            contact_person=contact_person,
            parent_id=parent_id,
            is_slave=True,
        )

        # 5. Запись в базу данных
        await self.repository.create(counterparty)
        await self.session.commit()

        return map_counterparty_to_response(counterparty)
