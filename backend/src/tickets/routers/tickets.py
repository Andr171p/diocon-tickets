from typing import Any

from uuid import UUID

from fastapi import APIRouter, Depends, status

from ...iam.dependencies import CurrentUserDep, get_current_user
from ...shared.dependencies import PageParamsDep
from ...shared.domain.exceptions import NotFoundError
from ...shared.schemas import Page
from ..dependencies import TicketFiltersDep, TicketRepoDep, TicketServiceDep
from ..infra.ai import predict_ticket_fields
from ..mappers import map_ticket_to_preview, map_ticket_to_response
from ..schemas import (
    PredictionResponse,
    TicketCreate,
    TicketPredict,
    TicketPreview,
    TicketResponse,
)

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


@router.get(
    path="/me",
    status_code=status.HTTP_200_OK,
    response_model=Page[TicketPreview],
    summary="Получение моих тикетов",
    description="Только те тикеты, где текущий пользователь записан как инициатор"
)
async def get_my_tickets(
        current_user: CurrentUserDep,
        params: PageParamsDep,
        repository: TicketRepoDep,
) -> Page[dict[str, Any]]:
    page = await repository.get_by_reporter(current_user.user_id, params)
    return page.to_response(map_ticket_to_preview)


@router.get(
    path="",
    status_code=status.HTTP_200_OK,
    response_model=Page[TicketPreview],
    summary="Получение всех тикетов с пагинацией",
    description="Метод предназначен для роли `support` и выше",
    dependencies=[Depends(get_current_user)]
)
async def get_tickets(
        params: PageParamsDep,
        filters: TicketFiltersDep,
        repository: TicketRepoDep,
) -> Page[dict[str, Any]]:
    ...


@router.get(
    path="/{ticket_id}",
    status_code=status.HTTP_200_OK,
    response_model=TicketResponse,
    dependencies=[Depends(get_current_user)],
    summary="Получение тикета по его ID"
)
async def get_ticket(ticket_id: UUID, repository: TicketRepoDep) -> TicketResponse:
    ticket = await repository.read(ticket_id)
    if ticket is None:
        raise NotFoundError(f"Ticket with ID {ticket_id} not found")
    return map_ticket_to_response(ticket)


@router.post(
    path="/predict",
    status_code=status.HTTP_200_OK,
    response_model=PredictionResponse,
    summary="Определение приоритета и генерация тегов"
)
async def predict_for_ticket(data: TicketPredict) -> PredictionResponse:
    return await predict_ticket_fields(data)
