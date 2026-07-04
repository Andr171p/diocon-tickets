from typing import Annotated

from uuid import UUID

from fastapi import Depends, Query
from pydantic import EmailStr

from src.shared.dependencies import PaginationDep, SessionDep
from src.shared.domain.repos import get_or_raise_404
from src.shared.schemas import Page

from .domain.entities import Counterparty
from .domain.repo import CounterpartyFilters, CounterpartyRepository
from .domain.vo import Inn
from .infra.repos import SqlCounterpartyRepository
from .mappers import map_counterparty_to_response
from .schemas import CounterpartyResponse
from .services import CounterpartyService


def get_counterparty_repo(session: SessionDep) -> SqlCounterpartyRepository:
    return SqlCounterpartyRepository(session)


CounterpartyRepoDep = Annotated[CounterpartyRepository, Depends(get_counterparty_repo)]


def get_counterparty_service(
        session: SessionDep, repo: CounterpartyRepoDep
) -> CounterpartyService:
    return CounterpartyService(session, repo)


CounterpartyServiceDep = Annotated[CounterpartyService, Depends(get_counterparty_service)]


def get_counterparty_filters(
        q: Annotated[
            str | None, Query(..., description="Поисковый запрос (наименования, инн)")
        ] = None,
        email: Annotated[
            EmailStr | None, Query(..., description="Email контрагента")
        ] = None,
        inn: Annotated[str | None, Query(..., description="ИНН контрагента")] = None,
) -> CounterpartyFilters:
    return CounterpartyFilters(search_query=q, email=email, inn=Inn(inn) if inn else None)


CounterpartyFiltersDep = Annotated[CounterpartyFilters, Depends(get_counterparty_filters)]


async def get_counterparty_or_404(
        counterparty_id: UUID, counterparty_repo: CounterpartyRepoDep
) -> CounterpartyResponse:
    counterparty = await get_or_raise_404(counterparty_repo.read, counterparty_id, Counterparty)
    return map_counterparty_to_response(counterparty)


async def paginate_counterparties(
        pagination: PaginationDep,
        filters: CounterpartyFiltersDep,
        counterparty_repo: CounterpartyRepoDep,
) -> Page[CounterpartyResponse]:
    page = await counterparty_repo.paginate(pagination, filters)
    return page.to_response(map_counterparty_to_response)
