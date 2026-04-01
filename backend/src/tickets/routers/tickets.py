from typing import Any

from fastapi import APIRouter, Depends, status

from ...iam.dependencies import CurrentSupportUserDep, CurrentUserDep
from ...shared.dependencies import PageParamsDep
from ...shared.schemas import Page
from ..dependencies import TicketRepoDep, TicketServiceDep
from ..mappers import map_ticket_to_preview
from ..schemas import TicketCreate, TicketResponse

router = APIRouter(prefix="/tickets", tags=["Тикеты"])


@router.post(
    path="",
    status_code=status.HTTP_201_CREATED,
    response_model=TicketResponse,
    summary="Создание нового тикета"
)
async def create_ticket(
        current_user: CurrentUserDep, data: TicketCreate, service: TicketServiceDep
) -> TicketResponse:
    return await service.create(
        data, created_by=current_user.user_id, created_by_role=current_user.role
    )


"""@router.get(
    path="",
    status_code=status.HTTP_200_OK,
    response_model=Page[TicketResponse],
    summary="Получение всех тикетов с пагинацией"
)
async def get_tickets(
        current_user: CurrentUserDep,
        filtering_params: ...,
        page_params: PageParamsDep,
        repository: TicketRepoDep,
) -> Page[dict[str, Any]]:
    ...
"""
