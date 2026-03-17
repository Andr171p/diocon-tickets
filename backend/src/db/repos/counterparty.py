from uuid import UUID

from sqlalchemy import insert, select, update

from ...core.entities import ContactPerson, Counterparty, User
from ..models import ContactPersonOrm, CounterpartyOrm, UserOrm
from .base import SqlAlchemyRepository


class CounterpartyRepository(SqlAlchemyRepository[Counterparty, CounterpartyOrm]):
    entity = Counterparty
    model = CounterpartyOrm

    async def add_contact_person(self, contact_person: ContactPerson) -> ContactPerson:
        stmt = (
            insert(ContactPersonOrm)
            .values(**contact_person.model_dump())
            .returning(ContactPersonOrm)
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one()
        await self.session.commit()
        return ContactPerson.model_validate(model)

    async def get_contact_person(self, counterparty_id: UUID) -> ContactPerson | None:
        stmt = select(ContactPersonOrm).where(ContactPersonOrm.counterparty_id == counterparty_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return None if model is None else ContactPerson.model_validate(model)

    async def update_contact_person(self, counterparty_id: UUID, **kwargs) -> ContactPerson:
        stmt = (
            update(ContactPersonOrm)
            .values(**kwargs)
            .where(ContactPersonOrm.counterparty_id == counterparty_id)
            .returning(ContactPersonOrm)
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        await self.session.commit()
        return None if model is None else ContactPerson.model_validate(model)

    async def get_customers(self, counterparty_id: UUID, page: int, limit: int) -> list[User]:
        offset = (page - 1) * limit
        stmt = (
            select(UserOrm)
            .where(UserOrm.counterparty_id == counterparty_id)
            .offset(offset)
            .limit(limit)
        )
        results = await self.session.execute(stmt)
        models = results.scalars().all()
        return [User.model_validate(model) for model in models]
