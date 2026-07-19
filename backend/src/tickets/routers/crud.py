from uuid import UUID

from fastapi import APIRouter, Depends, status

from src.iam.dependencies import CurrentSubjectDep, get_current_subject
from src.tickets.dependencies import TicketServiceDep, get_ticket_or_404
from src.tickets.schemas import TicketCreate, TicketResponse, TicketUpdate

router = APIRouter(prefix="/tickets", tags=["Заявки | CRUD"])


@router.post(
    path="",
    status_code=status.HTTP_201_CREATED,
    response_model=TicketResponse,
    summary="Создать заявку",
)
async def create_ticket(
        data: TicketCreate, current_subject: CurrentSubjectDep, service: TicketServiceDep,
) -> TicketResponse:
    return await service.create(data=data, current_subject=current_subject)


@router.patch(
    path="/{ticket_id}",
    status_code=status.HTTP_200_OK,
    response_model=TicketResponse,
    summary="Обновить заявку",
)
async def update_ticket(
        ticket_id: UUID,
        data: TicketUpdate,
        current_subject: CurrentSubjectDep,
        service: TicketServiceDep,
) -> TicketResponse:
    return await service.edit(ticket_id=ticket_id, data=data, current_subject=current_subject)


@router.get(
    path="/{ticket_id}",
    status_code=status.HTTP_200_OK,
    response_model=TicketResponse,
    dependencies=[Depends(get_current_subject)],
    summary="Получить заявку",
)
async def get_ticket(ticket: TicketResponse = Depends(get_ticket_or_404)) -> TicketResponse:
    return ticket


@router.delete(
    path="/{ticket_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить заявку",
)
async def delete_ticket(
        ticket_id: UUID, current_subject: CurrentSubjectDep, service: TicketServiceDep,
) -> None:
    return await service.archive(ticket_id=ticket_id, current_subject=current_subject)
