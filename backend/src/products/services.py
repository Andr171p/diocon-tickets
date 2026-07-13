from sqlalchemy.ext.asyncio import AsyncSession

from src.iam.domain.authz import Subject

from .domain.entities import SoftwareProduct
from .domain.repo import ProductRepository
from .domain.vo import ProductStatus
from .mappers import map_product_to_response
from .schemas import ProductCreate, ProductResponse, validate_product_attributes


class ProductService:
    def __init__(self, session: AsyncSession, repository: ProductRepository) -> None:
        self.session = session
        self.repository = repository

    async def create(self, data: ProductCreate, current_subject: Subject) -> ProductResponse:
        """Создание программного продукта"""

        if data.status not in {ProductStatus.ACTIVE, ProductStatus.BETA}:
            raise ValueError("Initial status must be active or beta")

        validate_product_attributes(data.category, data.attributes)

        product = SoftwareProduct(
            name=data.name,
            vendor=data.vendor,
            version=data.version,
            description=data.description,
            category=data.category,
            status=data.status,
            attributes=data.attributes,
            created_by=current_subject.id,
        )
        await self.repository.create(product)
        await self.session.commit()

        return map_product_to_response(product)
