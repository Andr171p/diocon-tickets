# Тестирование Use cases

from unittest.mock import AsyncMock

import pytest

from src.counterparties.domain.vo import CounterpartyType
from src.counterparties.schemas import ContactPersonIn, CounterpartyCreate
from src.counterparties.services import CounterpartyService


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


# ====================== Тесты для сервисов контрагента ======================


@pytest.mark.asyncio
async def test_create_counterparty_success(legal_entity_data, mock_counterparty_repo):
    service = CounterpartyService(session=AsyncMock(), repository=mock_counterparty_repo)

    response = await service.create(legal_entity_data)

    assert response.id is not None


@pytest.mark.asyncio
async def test_add_branch_to_exists_counterparty(
        legal_entity_data, branch_data, mock_counterparty_repo
):
    service = CounterpartyService(session=AsyncMock(), repository=mock_counterparty_repo)

    counterparty = await service.create(legal_entity_data)
    response = await service.add_branch(counterparty.id, branch_data)

    assert response.id is not None
