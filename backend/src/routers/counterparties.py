from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from ..core.entities import ContactPerson, Counterparty
from ..db.repos import CounterpartyRepository
from ..dependencies import get_counterparty_repo
from ..schemas import (
    ContactPersonAdd,
    ContactPersonUpdate,
    CounterpartyCreate,
    CounterpartyUpdate,
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Counterparty with ID {counterparty_id} not found",
            headers={"X-Error-Code": "COUNTERPARTY_NOT_FOUND"}
        )
    return counterparty


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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Counterparty with ID {counterparty_id} not found",
            headers={"X-Error-Code": "COUNTERPARTY_NOT_FOUND"}
        )
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Counterparty with ID {counterparty_id} not found",
            headers={"X-Error-Code": "COUNTERPARTY_NOT_FOUND"},
        )
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contact person not found for counterparty with ID {counterparty_id}",
            headers={"X-Error-Code": "CONTACT_PERSON_NOT_FOUND"},
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contact person not found for counterparty with ID {counterparty_id}",
            headers={"X-Error-Code": "CONTACT_PERSON_NOT_FOUND"},
        )
    return contact_person
