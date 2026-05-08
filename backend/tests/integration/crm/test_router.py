from uuid import uuid4

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient

from src.crm.dependencies import get_counterparty_repo, get_counterparty_service
from src.crm.infra.repos import SqlCounterpartyRepository
from src.crm.services import CounterpartyService
from src.iam.dependencies import get_current_user
from src.iam.domain.services import create_customer
from src.iam.domain.vo import UserRole
from src.iam.infra.repos import SqlUserRepository
from src.products.domain.entities import SoftwareProduct
from src.products.domain.vo import ProductCategory, ProductStatus
from src.products.infra.repo import SqlProductRepository


@pytest.fixture
def counterparty_repo(session):
    return SqlCounterpartyRepository(session)


@pytest.fixture
def user_repo(session):
    return SqlUserRepository(session)


@pytest.fixture
def product_repo(session):
    return SqlProductRepository(session)


@pytest.fixture
async def crm_client(session, counterparty_repo, current_admin_user):
    from main import app

    service = CounterpartyService(session=session, repository=counterparty_repo)

    app.dependency_overrides[get_counterparty_repo] = lambda: counterparty_repo
    app.dependency_overrides[get_counterparty_service] = lambda: service
    app.dependency_overrides[get_current_user] = lambda: current_admin_user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

    app.dependency_overrides = {}


@pytest.fixture
def legal_entity_payload():
    uid = uuid4()
    return {
        "counterparty_type": "Юридическое лицо",
        "name": f"Головная компания {uid}",
        "legal_name": f"ООО Головная компания {uid}",
        "inn": f"{uid.int % 10**10:010d}",
        "kpp": "123456789",
        "phone": "88005553535",
        "email": f"parent-{uid}@example.com",
        "address": "Москва, ул. Ленина, д.1",
        "contact_persons": [{
            "first_name": "Иван",
            "last_name": "Иванов",
            "middle_name": "Иванович",
            "phone": "88005553535",
            "email": "ivanov@example.com",
        }],
    }


@pytest.fixture
def branch_payload():
    uid = uuid4()
    return {
        "name": f"Филиал {uid}",
        "legal_name": f"ООО Головная компания (филиал) {uid}",
        "kpp": "987654321",
        "phone": "88005553536",
        "email": f"branch-{uid}@example.com",
        "address": "Санкт-Петербург, Невский пр., д.10",
    }


@pytest.fixture
def contact_person_payload():
    return {
        "first_name": "Петр",
        "last_name": "Петров",
        "middle_name": "Петрович",
        "phone": "88005553537",
        "email": f"petrov-{uuid4()}@example.com",
        "messengers": {"telegram": "petrov"},
    }


def make_product(name: str | None = None) -> SoftwareProduct:
    return SoftwareProduct(
        name=name or f"Product {uuid4()}",
        vendor="Test Vendor",
        category=ProductCategory.WEB,
        description="Test product",
        version="1.0",
        status=ProductStatus.ACTIVE,
        attributes={"kind": "test"},
    )


@pytest.mark.asyncio
async def test_create_counterparty(client, legal_entity_payload):
    # 1. Создание
    response = await client.post(url="/api/v1/counterparties", json=legal_entity_payload)

    assert response.status_code == status.HTTP_201_CREATED

    counterparty_id = response.json()["id"]

    # 2. Получение через API
    response = await client.get(url=f"/api/v1/counterparties/{counterparty_id}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["phone"] == "+7 (800) 555-35-35"


@pytest.mark.asyncio
async def test_add_branch_counterparty(client, legal_entity_payload, branch_payload):
    # 1. Создание основного контрагента
    response = await client.post(url="/api/v1/counterparties", json=legal_entity_payload)

    assert response.status_code == status.HTTP_201_CREATED

    counterparty_id = response.json()["id"]

    # 2. Добавление филиала
    response = await client.post(
        url=f"/api/v1/counterparties/{counterparty_id}", json=branch_payload
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["phone"] == "+7 (800) 555-35-36"


@pytest.mark.asyncio
async def test_get_counterparty_not_found_returns_404(crm_client):
    """
    Проверяем API получения контрагента: он должен вернуть 404,
    если контрагент с переданным id не найден.
    Данные: случайный UUID, которого нет в реальной БД.
    """
    counterparty_id = uuid4()

    response = await crm_client.get(f"/api/v1/counterparties/{counterparty_id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    data = response.json()
    assert data["error"]["code"] == "RESOURCE_NOT_FOUND"
    assert str(counterparty_id) in data["error"]["message"]


@pytest.mark.asyncio
async def test_get_counterparties_returns_page(crm_client, legal_entity_payload):
    """
    Проверяем API списка контрагентов: он нужен, чтобы вернуть страницу
    контрагентов из реального SQL-репозитория.
    Данные: созданный через API головной контрагент.
    """
    created_response = await crm_client.post(
        url="/api/v1/counterparties",
        json=legal_entity_payload,
    )
    assert created_response.status_code == status.HTTP_201_CREATED
    counterparty_id = created_response.json()["id"]

    response = await crm_client.get("/api/v1/counterparties", params={"page": 1, "size": 10})

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    found_ids = {item["id"] for item in data["items"]}
    assert counterparty_id in found_ids


@pytest.mark.asyncio
async def test_delete_counterparty_marks_inactive(
    crm_client, counterparty_repo, legal_entity_payload
):
    """
    Проверяем API удаления контрагента: он должен пометить контрагента
    неактивным через SQL-репозиторий.
    Данные: созданный через API головной контрагент.
    """
    created_response = await crm_client.post(
        url="/api/v1/counterparties",
        json=legal_entity_payload,
    )
    assert created_response.status_code == status.HTTP_201_CREATED
    counterparty_id = created_response.json()["id"]

    response = await crm_client.delete(f"/api/v1/counterparties/{counterparty_id}")

    assert response.status_code == status.HTTP_204_NO_CONTENT
    counterparty = await counterparty_repo.read(counterparty_id)
    assert counterparty is not None
    assert counterparty.is_active is False


@pytest.mark.asyncio
async def test_add_contact_person_returns_updated_counterparty(
    crm_client, legal_entity_payload, contact_person_payload
):
    """
    Проверяем API добавления контактного лица: он должен сохранить контакт
    у существующего контрагента и вернуть обновленную response-схему.
    Данные: созданный через API контрагент и новое контактное лицо.
    """
    created_response = await crm_client.post(
        url="/api/v1/counterparties",
        json=legal_entity_payload,
    )
    assert created_response.status_code == status.HTTP_201_CREATED
    counterparty_id = created_response.json()["id"]

    response = await crm_client.post(
        url=f"/api/v1/counterparties/{counterparty_id}/contact-persons",
        json=contact_person_payload,
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert any(
        contact_person["email"] == contact_person_payload["email"]
        for contact_person in data["contact_persons"]
    )


@pytest.mark.asyncio
async def test_get_counterparty_customers_returns_page(
    crm_client, legal_entity_payload, user_repo
):
    """
    Проверяем API клиентов контрагента: он должен вернуть страницу
    пользователей, привязанных к конкретному контрагенту.
    Данные: созданный контрагент и customer-пользователь в реальной БД.
    """
    created_response = await crm_client.post(
        url="/api/v1/counterparties",
        json=legal_entity_payload,
    )
    assert created_response.status_code == status.HTTP_201_CREATED
    counterparty_id = created_response.json()["id"]

    customer = create_customer(
        email=f"customer-{uuid4()}@example.com",
        password_hash=f"hashed-password-{uuid4()}",
        counterparty_id=counterparty_id,
        user_role=UserRole.CUSTOMER,
    )
    await user_repo.create(customer)
    await user_repo.session.commit()

    response = await crm_client.get(
        f"/api/v1/counterparties/{counterparty_id}/customers",
        params={"page": 1, "size": 10},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    found_ids = {item["id"] for item in data["items"]}
    assert str(customer.id) in found_ids


@pytest.mark.asyncio
async def test_link_and_get_counterparty_products(
    crm_client, legal_entity_payload, product_repo
):
    """
    Проверяем API продуктов контрагента: он должен привязать программный
    продукт к контрагенту и затем вернуть его в списке продуктов.
    Данные: созданный контрагент и программный продукт в реальной БД.
    """
    created_response = await crm_client.post(
        url="/api/v1/counterparties",
        json=legal_entity_payload,
    )
    assert created_response.status_code == status.HTTP_201_CREATED
    counterparty_id = created_response.json()["id"]

    product = make_product()
    await product_repo.create(product)
    await product_repo.session.commit()

    link_response = await crm_client.post(
        url=f"/api/v1/counterparties/{counterparty_id}/products",
        json={"product_id": str(product.id)},
    )

    assert link_response.status_code == status.HTTP_201_CREATED
    assert link_response.json()["message"] == "Software product linked successfully"

    response = await crm_client.get(
        f"/api/v1/counterparties/{counterparty_id}/products",
        params={"page": 1, "size": 10},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    found_ids = {item["id"] for item in data["items"]}
    assert str(product.id) in found_ids

@pytest.mark.asyncio
async def test_create_counterparty_duplicate_inn_returns_409(crm_client, legal_entity_payload):
    """
    Проверяем API создания контрагента: он должен вернуть 409,
    если головной контрагент с таким ИНН уже существует.
    Данные: два запроса с одинаковым inn и разными email.
    """
    first_response = await crm_client.post(
        url="/api/v1/counterparties",
        json=legal_entity_payload,
    )
    assert first_response.status_code == status.HTTP_201_CREATED

    duplicate_payload = {
        **legal_entity_payload,
        "email": f"another-{uuid4()}@example.com",
    }

    response = await crm_client.post(
        url="/api/v1/counterparties",
        json=duplicate_payload,
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    data = response.json()
    assert data["error"]["code"] == "ALREADY_EXISTS"
    assert "INN" in data["error"]["message"]

@pytest.mark.asyncio
async def test_create_counterparty_duplicate_email_returns_409(crm_client, legal_entity_payload):
    """
    Проверяем API создания контрагента: он должен вернуть 409,
    если email уже используется другим головным контрагентом.
    Данные: два запроса с одинаковым email и разными inn.
    """
    first_response = await crm_client.post(
        url="/api/v1/counterparties",
        json=legal_entity_payload,
    )
    assert first_response.status_code == status.HTTP_201_CREATED

    duplicate_payload = {
        **legal_entity_payload,
        "inn": f"{uuid4().int % 10**10:010d}",
    }

    response = await crm_client.post(
        url="/api/v1/counterparties",
        json=duplicate_payload,
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    data = response.json()
    assert data["error"]["code"] == "ALREADY_EXISTS"
    assert "email" in data["error"]["message"]

@pytest.mark.asyncio
async def test_add_branch_parent_not_found_returns_404(crm_client, branch_payload):
    """
    Проверяем API добавления филиала: он должен вернуть 404,
    если головной контрагент с переданным id не найден.
    Данные: случайный id и валидная форма филиала.
    """
    counterparty_id = uuid4()

    response = await crm_client.post(
        url=f"/api/v1/counterparties/{counterparty_id}",
        json=branch_payload,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    data = response.json()
    assert data["error"]["code"] == "RESOURCE_NOT_FOUND"
    assert str(counterparty_id) in data["error"]["message"]

@pytest.mark.asyncio
async def test_link_product_counterparty_not_found_returns_404(crm_client, product_repo):
    """
    Проверяем API привязки продукта: он должен вернуть 404,
    если контрагент с переданным id не найден.
    Данные: существующий программный продукт и случайный id контрагента.
    """
    product = make_product()
    await product_repo.create(product)
    await product_repo.session.commit()

    counterparty_id = uuid4()

    response = await crm_client.post(
        url=f"/api/v1/counterparties/{counterparty_id}/products",
        json={"product_id": str(product.id)},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    data = response.json()
    assert data["error"]["code"] == "RESOURCE_NOT_FOUND"
    assert str(counterparty_id) in data["error"]["message"]
