from typing import Annotated

from uuid import UUID

from fastapi import APIRouter, Body, status

from src.iam.dependencies import CurrentSubjectDep
from src.tickets.dependencies import TicketServiceDep
from src.tickets.schemas import TicketResponse

router = APIRouter(prefix="/tickets", tags=["Заявки | Управление состоянием"])


@router.post(
    path="/{ticket_id}/assign",
    status_code=status.HTTP_200_OK,
    response_model=TicketResponse,
    summary="Назначить исполнителя",
)
async def assign_to_ticket(
        ticket_id: UUID,
        assignee_id: Annotated[UUID, Body(description="Идентификатор пользователя")],
        current_subject: CurrentSubjectDep,
        service: TicketServiceDep,
) -> TicketResponse:
    return await service.assign(
        ticket_id=ticket_id, assignee_id=assignee_id, current_subject=current_subject,
    )


@router.post(
    path="/{ticket_id}/start-progress",
    status_code=status.HTTP_200_OK,
    response_model=TicketResponse,
    summary="Начать работу над заявкой",
)
async def start_ticket_progress(
        ticket_id: UUID, current_subject: CurrentSubjectDep, service: TicketServiceDep,
) -> TicketResponse:
    return await service.start_progress(ticket_id=ticket_id, current_subject=current_subject)


@router.post(
    path="/{ticket_id}/resolve",
    status_code=status.HTTP_200_OK,
    response_model=TicketResponse,
    summary="Решить заявку",
)
async def resolve_ticket(
        ticket_id: UUID, current_subject: CurrentSubjectDep, service: TicketServiceDep,
) -> TicketResponse:
    return await service.resolve(ticket_id=ticket_id, current_subject=current_subject)
