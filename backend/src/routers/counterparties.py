from uuid import UUID

from fastapi import APIRouter, Depends, status

from ..core.entities import ContactPerson, Counterparty
from ..core.errors import NotFoundError
from ..db.repos import CounterpartyRepository
from ..dependencies import get_counterparty_repo, get_pagination
from ..schemas import (
    ContactPersonAdd,
    ContactPersonUpdate,
    CounterpartyCreate,
    CounterpartyUpdate,
    UserResponse,
)

router = APIRouter(prefix="/counterparties", tags=["Контрагенты"])


@router.post(
    path="",
    status_code=status.HTTP_201_CREATED,
    response_model=Counterparty,
    summary="Создание контрагента"
)
async def create_counterparty(
        data: CounterpartyCreate,
        repository: CounterpartyRepository = Depends(get_counterparty_repo),
) -> Counterparty:
    return await repository.create(Counterparty.model_validate(data))


@router.get(
    path="/{counterparty_id}",
    status_code=status.HTTP_200_OK,
    response_model=Counterparty,
    summary="Получение контрагента"
)
async def get_counterparty(
        counterparty_id: UUID,
        repository: CounterpartyRepository = Depends(get_counterparty_repo),
) -> Counterparty:
    counterparty = await repository.read(counterparty_id)
    if counterparty is None:
        raise NotFoundError(f"Counterparty with ID {counterparty_id} not found")
    return counterparty


@router.get(
    path="",
    status_code=status.HTTP_200_OK,
    response_model=list[Counterparty],
    summary="Получение списка контрагентов"
)
async def get_counterparties(
        pagination: tuple[int, int] = Depends(get_pagination),
        repository: CounterpartyRepository = Depends(get_counterparty_repo),
) -> list[Counterparty]:
    page, limit = pagination
    return await repository.read_all(page, limit)


@router.patch(
    path="/{counterparty_id}",
    status_code=status.HTTP_200_OK,
    response_model=Counterparty,
    summary="Обновление свойств контрагента"
)
async def update_counterparty(
        counterparty_id: UUID,
        data: CounterpartyUpdate,
        repository: CounterpartyRepository = Depends(get_counterparty_repo),
) -> Counterparty:
    counterparty = await repository.update(counterparty_id, **data.model_dump(exclude_none=True))
    if counterparty is None:
        raise NotFoundError(f"Counterparty with ID {counterparty_id} not found")
    return counterparty


@router.delete(
    path="/{counterparty_id}",
    status_code=status.HTTP_200_OK,
    response_model=Counterparty,
    summary="Удаление контрагента",
    description="Soft-delete метод, меняет поле `is_active` на `false`"
)
async def delete_counterparty(
        counterparty_id: UUID,
        repository: CounterpartyRepository = Depends(get_counterparty_repo),
) -> Counterparty:
    counterparty = await repository.update(counterparty_id, is_active=False)
    if counterparty is None:
        raise NotFoundError(f"Counterparty with ID {counterparty_id} not found")
    return counterparty


@router.post(
    path="/{counterparty_id}/contact-person",
    status_code=status.HTTP_201_CREATED,
    response_model=ContactPerson,
    summary="Добавление контактного лица"
)
async def add_contact_person(
        counterparty_id: UUID,
        data: ContactPersonAdd,
        repository: CounterpartyRepository = Depends(get_counterparty_repo),
) -> ContactPerson:
    return await repository.add_contact_person(
        ContactPerson.model_validate(
            {"counterparty_id": counterparty_id, **data.model_dump()}
        )
    )


@router.get(
    path="/{counterparty_id}/contact-person",
    status_code=status.HTTP_200_OK,
    response_model=ContactPerson,
    summary="Получение контактного лица контрагента"
)
async def get_contact_person(
        counterparty_id: UUID,
        repository: CounterpartyRepository = Depends(get_counterparty_repo),
) -> ContactPerson:
    contact_person = await repository.get_contact_person(counterparty_id)
    if contact_person is None:
        raise NotFoundError(
            f"Contact person not found for counterparty with ID '{counterparty_id}'"
        )
    return contact_person


@router.patch(
    path="/{counterparty_id}/contact-person",
    status_code=status.HTTP_200_OK,
    response_model=ContactPerson,
    summary="Обновление контактного лица контрагента"
)
async def update_contact_person(
        counterparty_id: UUID,
        data: ContactPersonUpdate,
        repository: CounterpartyRepository = Depends(get_counterparty_repo),
) -> ContactPerson:
    contact_person = await repository.update_contact_person(
        counterparty_id, **data.model_dump(exclude_none=True)
    )
    if contact_person is None:
        raise NotFoundError(
            f"Contact person not found for counterparty with ID '{counterparty_id}'"
        )
    return contact_person


@router.get(
    path="/{counterparty_id}/customers",
    status_code=status.HTTP_200_OK,
    response_model=list[UserResponse],
    summary="Получение клиентов внутри контрагента"
)
async def get_customers(
        counterparty_id: UUID,
        pagination: tuple[int, int] = Depends(get_pagination),
        repository: CounterpartyRepository = Depends(get_counterparty_repo),
) -> list[UserResponse]:
    page, limit = pagination
    users = await repository.get_customers(counterparty_id, page, limit)
    return [UserResponse.model_validate(user) for user in users]
