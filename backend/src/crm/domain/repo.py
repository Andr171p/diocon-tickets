from typing import override

from dataclasses import dataclass
from uuid import UUID

from src.iam.domain.entities import User
from src.products.domain.entities import SoftwareProduct
from src.shared.domain.repos import Repository
from src.shared.schemas import Page, Pagination

from .entities import Counterparty
from .vo import Inn


@dataclass(frozen=True)
class CounterpartyFilters:
    search_query: str | None = None
    email: str | None = None
    inn: Inn | None = None


class CounterpartyRepository(Repository[Counterparty]):

    @override
    async def paginate(
            self, pagination: Pagination, filters: CounterpartyFilters | None = None,
    ) -> Page[Counterparty]: ...

    async def get_by_email(self, email: str) -> Counterparty | None: ...

    async def get_by_inn(self, inn: Inn) -> Counterparty | None: ...

    async def get_with_descendants(self, counterparty_id: UUID) -> list[Counterparty]:
        """
        Нахождение контрагента и всех его суб-компании (филиалов, дочерних отделов).
        Принимает ID головного контрагента и возвращает плоский список.
        """

    async def get_customers(self, counterparty_id: UUID, params: Pagination) -> Page[User]:
        """Получение клиентов контрагента"""

    async def link_product(self, counterparty_id: UUID, product_id: UUID) -> None:
        """
        Привязка программного продукта к контрагенту
        """

    async def get_products(
            self, counterparty_id: UUID, params: Pagination
    ) -> Page[SoftwareProduct]:
        """
        Получение программных продуктов, которые используются контрагентом
        """
