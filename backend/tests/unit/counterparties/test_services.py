# Тестирование Use cases

from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from src.counterparties.domain.entities import Counterparty
from src.counterparties.domain.vo import CounterpartyType, Inn
from src.counterparties.schemas import ContactPersonIn, CounterpartyCreate
from src.counterparties.services import CounterpartyService
from src.shared.infra.repos import InMemoryRepository


@pytest.fixture
def legal_entity_data():
    return CounterpartyCreate(
        counterparty_type=CounterpartyType.LEGAL_ENTITY,
        name="Головная компания",
        legal_name="ООО Головная компания",
        inn="1234567890",
        kpp="123456789",
        phone="88005553535",
        email="parent@example.com",
        address="Москва, ул. Ленина, д.1",
        contact_person=ContactPersonIn(
            first_name="Иван",
            last_name="Иванов",
            middle_name="Иванович",
            phone="88005553535",
            email="ivanov@example.com",
        ),
    )


@pytest.fixture
def branch_data():
    return CounterpartyCreate(
        counterparty_type=CounterpartyType.BRANCH,
        name="Филиал",
        legal_name="ООО Головная компания (филиал)",
        inn="1234567890",
        kpp="987654321",
        phone="88005553536",
        email="branch@example.com",
        address="Санкт-Петербург, Невский пр., д.10",
        contact_person=ContactPersonIn(
            first_name="Петр",
            last_name="Петров",
            middle_name="Петрович",
            phone="88005553536",
            email="petrov@example.com",
        ),
    )

# ====================== In memory реализация для DIP ======================


class InMemoryCounterpartyRepository(InMemoryRepository[Counterparty]):
    async def get_by_email(self, email: str) -> Counterparty | None:
        for entity in self.data.values():
            if entity.email == email:
                return entity
        return None

    async def get_by_inn(self, inn: Inn) -> Counterparty | None:
        for entity in self.data.values():
            if entity.inn == inn:
                return entity
        return None

    async def get_with_descendants(self, counterparty_id: UUID) -> list[Counterparty]:
        return [entity for entity in self.data.values() if entity.parent_id == counterparty_id]


# ====================== Тесты для сценариев работы с контрагентом ======================


@pytest.mark.asyncio
async def test_create_counterparty_success(legal_entity_data):
    repo = InMemoryCounterpartyRepository()
    service = CounterpartyService(session=AsyncMock(), repository=repo)

    response = await service.create(legal_entity_data)

    assert response.id is not None


@pytest.mark.asyncio
async def test_add_slave_to_exists_counterparty(legal_entity_data, branch_data):
    repo = InMemoryCounterpartyRepository()
    service = CounterpartyService(session=AsyncMock(), repository=repo)

    counterparty = await service.create(legal_entity_data)
    response = await service.add_branch(counterparty.id, branch_data)

    assert response.id is not None
