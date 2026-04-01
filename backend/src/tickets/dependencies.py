from typing import Annotated

from fastapi import Depends

from ..shared.dependencies import EventPublisherDep, SessionDep
from .domain.repo import TicketRepository
from .infra.repo import SqlTicketRepository
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


def get_filtering_params(): ...
