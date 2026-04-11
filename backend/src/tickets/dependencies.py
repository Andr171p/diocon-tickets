from typing import Annotated

from uuid import UUID

from fastapi import Depends, Query

from ..shared.dependencies import EventPublisherDep, SessionDep
from .domain.repos import ProjectRepository, TicketRepository
from .domain.vo import TicketPriority, TicketStatus
from .infra.repos import SqlProjectRepository, SqlTicketRepository
from .schemas import TicketFilter
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


def get_ticket_filters(
        reporter_id: Annotated[
            UUID | None, Query(..., description="По инициатору")
        ] = None,
        created_by: Annotated[
            UUID | None, Query(..., description="По фактическому создателю")
        ] = None,
        project_id: Annotated[
            UUID | None, Query(..., description="По проекту")
        ] = None,
        counterparty_id: Annotated[
            UUID | None, Query(..., description="По контрагенту")
        ] = None,
        status: Annotated[
            TicketStatus | None,
            Query(..., description="По статусу")
        ] = None,
        priority: Annotated[
            TicketPriority | None,
            Query(..., description="По приоритету")
        ] = None,
        # Дополнительные фильтры
        tags: Annotated[
            list[str] | None, Query(..., description="По тегам")
        ] = None,
) -> TicketFilter:
    return TicketFilter(
        reporter_id=reporter_id,
        created_by=created_by,
        project_id=project_id,
        counterparty_id=counterparty_id,
        status=status,
        priority=priority,
        tags=tags,
    )


TicketFiltersDep = Annotated[TicketFilter, Depends(get_ticket_filters)]
