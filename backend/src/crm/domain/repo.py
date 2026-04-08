from uuid import UUID

from ...iam.domain.entities import User
from ...shared.domain.repo import Repository
from ...shared.schemas import Page, PageParams
from .entities import Counterparty
from .vo import Inn


class CounterpartyRepository(Repository[Counterparty]):

    async def get_by_email(self, email: str) -> Counterparty | None:
        """Поиск по email адресу компании (почта уникальна)"""

    async def get_by_inn(self, inn: Inn) -> Counterparty | None:
        """
        Поиск по ИНН основной компании
        (ИНН одинаковый для головной компании и её филиалов).
        """

    async def get_with_descendants(self, counterparty_id: UUID) -> list[Counterparty]:
        """
        Нахождение контрагента и всех его суб-компании (филиалов, дочерних отделов).
        Принимает ID головного контрагента и возвращает плоский список.
        """

    async def get_customers(self, counterparty_id: UUID, params: PageParams) -> Page[User]:
        """Получение клиентов контрагента"""
