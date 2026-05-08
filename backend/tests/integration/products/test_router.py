from uuid import uuid4

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient

from src.core.database import get_db
from src.iam.dependencies import get_current_user
from src.iam.domain.vo import UserRole
from src.iam.schemas import CurrentUser
from src.products.domain.entities import SoftwareProduct
from src.products.domain.vo import ProductCategory, ProductStatus
from src.products.infra.repo import SqlProductRepository


@pytest.fixture
def product_repo(session):
    return SqlProductRepository(session)


@pytest.fixture
def current_support_user():
    return CurrentUser(
        user_id=uuid4(),
        email="support@example.com",
        role=UserRole.SUPPORT_MANAGER,
    )


@pytest.fixture
async def products_client(session, current_support_user):
    from main import app

    async def override_get_db():  # noqa: RUF029
        yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: current_support_user

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_create_product_returns_created_product(products_client):
    """
    Проверяем API создания продукта: он должен принять HTTP-запрос,
    собрать ProductService через dependencies и сохранить продукт в реальную БД.
    Данные: WEB-продукт со статусом ACTIVE и валидными attributes.
    """
    payload = {
        "name": f"Portal {uuid4()}",
        "vendor": "Test Vendor",
        "category": ProductCategory.WEB,
        "description": "Test web product",
        "version": "1.0",
        "status": ProductStatus.ACTIVE,
        "attributes": {
            "environment": "production",
            "base_url": "https://example.com",
        },
    }

    response = await products_client.post("/api/v1/products", json=payload)

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == payload["name"]
    assert data["vendor"] == payload["vendor"]
    assert data["category"] == payload["category"]
    assert data["status"] == payload["status"]
    assert data["display_name"] == f"{payload['vendor']} {payload['name']} ({payload['version']})"


@pytest.mark.asyncio
async def test_get_products_filters_by_category_and_status(products_client, product_repo):
    """
    Проверяем API списка продуктов: он должен передать query-параметры
    category/status в ProductFilters и вернуть страницу из SQL-репозитория.
    Данные: WEB ACTIVE продукт и ERP BETA продукт в реальной БД.
    """
    web_product = SoftwareProduct(
        name=f"Web Product {uuid4()}",
        vendor="Vendor",
        category=ProductCategory.WEB,
        status=ProductStatus.ACTIVE,
        attributes={},
    )
    erp_product = SoftwareProduct(
        name=f"ERP Product {uuid4()}",
        vendor="Vendor",
        category=ProductCategory.ERP,
        status=ProductStatus.BETA,
        attributes={},
    )
    await product_repo.create(web_product)
    await product_repo.create(erp_product)
    await product_repo.session.commit()

    response = await products_client.get(
        "/api/v1/products",
        params={
            "page": 1,
            "size": 10,
            "category": ProductCategory.WEB,
            "status": ProductStatus.ACTIVE,
        },
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    found_ids = {item["id"] for item in data["items"]}
    assert str(web_product.id) in found_ids
    assert str(erp_product.id) not in found_ids


@pytest.mark.asyncio
async def test_get_product_category_attributes_schema(products_client):
    """
    Проверяем API получения схемы attributes: он нужен, чтобы frontend знал,
    какие дополнительные поля показывать для выбранной категории продукта.
    Данные: категория WEB.
    """
    response = await products_client.get(
        f"/api/v1/products/categories/{ProductCategory.WEB}/attributes-schema"
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["category"] == ProductCategory.WEB
    assert "$schema" in data["schema"]
    assert "properties" in data["schema"]
