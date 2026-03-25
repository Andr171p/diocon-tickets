from uuid import UUID

from sqlalchemy import select

from ...iam.domain.vo import FullName
from ...shared.infra.repos import ModelMapper, SqlAlchemyRepository
from ..domain.entities import Counterparty
from ..domain.vo import ContactPerson, Inn, Kpp, Okpo, Phone
from .models import CounterpartyOrm


class CounterpartyMapper(ModelMapper[Counterparty, CounterpartyOrm]):

    @staticmethod
    def to_entity(model: CounterpartyOrm) -> Counterparty:
        return Counterparty(
            id=model.id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            counterparty_type=model.counterparty_type,
            name=model.name,
            legal_name=model.legal_name,
            inn=Inn(model.inn),
            kpp=None if model.kpp is None else Kpp(model.kpp),
            okpo=None if model.okpo is None else Okpo(model.okpo),
            phone=None if model.phone is None else Phone(model.phone),
            email=model.email,
            address=model.address,
            avatar_url=model.avatar_url,
            contact_person=(
                None if model.contact_person is None
                else ContactPerson(
                    full_name=FullName(model.contact_person["full_name"]),
                    phone=Phone(model.contact_person["phone"]),
                    email=model.contact_person["email"],
                    messengers=model.contact_person["messengers"],
                )
            ),
            is_active=model.is_active,
            parent_id=model.parent_id,
            is_slave=model.is_slave,
        )

    @staticmethod
    def from_entity(entity: Counterparty) -> CounterpartyOrm:
        return CounterpartyOrm(
            id=entity.id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            counterparty_type=entity.counterparty_type,
            name=entity.name,
            legal_name=entity.legal_name,
            inn=entity.inn.value,
            kpp=entity.kpp.value,
            okpo=entity.okpo.value,
            phone=entity.phone.value,
            email=entity.email,
            address=entity.address,
            avatar_url=entity.avatar_url,
            contact_person=(
                None if entity.contact_person is None else {
                    "full_name": entity.contact_person.full_name.value,
                    "phone": entity.contact_person.phone.value,
                    "email": entity.contact_person.email,
                    "messengers": entity.contact_person.messengers,
                }
            ),
            is_active=entity.is_active,
            parent_id=entity.parent_id,
            is_slave=entity.is_slave,
        )


class SqlCounterpartyRepository(SqlAlchemyRepository[Counterparty, CounterpartyOrm]):
    model = CounterpartyOrm
    model_mapper = CounterpartyMapper

    async def get_by_email(self, email: str) -> Counterparty | None:
        stmt = (
            select(self.model)
            .where(
                (self.model.email == email) &
                (self.model.parent_id is None)
            )
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return None if model is None else self.model_mapper.to_entity(model)

    async def get_by_inn(self, inn: Inn) -> Counterparty | None:
        stmt = (
            select(self.model)
            .where(
                (self.model.inn == inn.value) &
                (self.model.parent_id is None)
            )
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return None if model is None else self.model_mapper.to_entity(model)

    async def get_with_descendants(self, counterparty_id: UUID) -> list[Counterparty]:
        # 1. Запрос для выбора корневого элемента
        recursive_cte = (
            select(self.model)
            .where(self.model.id == counterparty_id)
            .cte(name="counterparty_tree", recursive=True)
        )

        # 2. Рекурсивная часть: присоединение детей и найденных родителей
        recursive_cte = recursive_cte.union_all(
            select(self.model).join(recursive_cte, self.model.id == recursive_cte.c.id)
        )

        # 3. Финальный запрос из CTE
        stmt = select(self.model).from_statement(select(recursive_cte))

        # 4. Выполнение запроса и преобразование результата
        results = await self.session.execute(stmt)
        models = results.scalars().all()
        return [self.model_mapper.to_entity(model) for model in models]
