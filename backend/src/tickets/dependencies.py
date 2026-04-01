from typing import Annotated

from fastapi import Depends, Query

from ..shared.dependencies import EventPublisherDep, SessionDep
from .domain.repo import TicketRepository
from .domain.vo import TicketPriority, TicketStatus
from .infra.repo import SqlTicketRepository
from .schemas import FilterParams
from .services import TicketService


def get_ticket_repo(session: SessionDep) -> TicketRepository:
    return SqlTicketRepository(session)


TicketRepoDep = Annotated[TicketRepository, Depends(get_ticket_repo)]


def get_ticket_service(
        session: SessionDep,
        repository: Annotated[TicketRepository, Depends(get_ticket_repo)],
        event_publisher: EventPublisherDep
) -> TicketService:
    return TicketService(session, repository=repository, event_publisher=event_publisher)


TicketServiceDep = Annotated[TicketService, Depends(get_ticket_service)]


def get_filter_params(
        status: Annotated[
            TicketStatus | None,
            Query(..., description="Фильтр по статусу")
        ] = None,
        priority: Annotated[
            TicketPriority | None,
            Query(..., description="Фильтр по приоритету")
        ] = None,
) -> FilteringParams:
    return FilterParams(status=status, priority=priority)


FilterParamsDep = Annotated[FilterParams, Depends(get_filter_params)]
