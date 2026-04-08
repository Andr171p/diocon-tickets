from typing import Annotated

from fastapi import Depends, Query

from ..shared.dependencies import EventPublisherDep, SessionDep
from .domain.repos import ProjectRepository, TicketRepository
from .domain.vo import TicketPriority, TicketStatus
from .infra.repos import SqlProjectRepository, SqlTicketRepository
from .schemas import FilterParams
from .services import ProjectService, TicketService


def get_ticket_repo(session: SessionDep) -> TicketRepository:
    return SqlTicketRepository(session)


def get_project_repo(session: SessionDep) -> ProjectRepository:
    return SqlProjectRepository(session)


ProjectRepoDep = Annotated[ProjectRepository, Depends(get_project_repo)]
TicketRepoDep = Annotated[TicketRepository, Depends(get_ticket_repo)]


def get_project_service(session: SessionDep, repository: ProjectRepoDep) -> ProjectService:
    return ProjectService(session, repository)


def get_ticket_service(
        session: SessionDep,
        repository: TicketRepoDep,
        event_publisher: EventPublisherDep
) -> TicketService:
    return TicketService(session, repository=repository, event_publisher=event_publisher)


ProjectServiceDep = Annotated[ProjectService, Depends(get_project_service)]
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
) -> FilterParams:
    return FilterParams(status=status, priority=priority)


FilterParamsDep = Annotated[FilterParams, Depends(get_filter_params)]
