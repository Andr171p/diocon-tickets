from uuid import uuid4

from src.contracts.domain.events import (
    ContractClosed,
    ContractPackageAdded,
    ContractReactivated,
    ContractSuspended,
    HoursConsumed,
)
from src.contracts.domain.vo import HoursPackageType


def test_create_hours_consumed_event_success():
    """
    Событие хранит данные о списанных часах
    """

    contract_id = uuid4()
    ticket_id = uuid4()
    user_id = uuid4()

    event = HoursConsumed(
        contract_id=contract_id,
        ticket_id=ticket_id,
        user_id=user_id,
        hours=2.5,
        remaining_hours=7.5,
    )

    assert event.contract_id == contract_id
    assert event.ticket_id == ticket_id
    assert event.user_id == user_id
    assert event.hours == 2.5
    assert event.remaining_hours == 7.5
    assert event.version == 1


def test_create_contract_package_added_event_success():
    """
    Событие хранит данные о добавленном пакете часов
    """

    contract_id = uuid4()
    added_by = uuid4()

    event = ContractPackageAdded(
        contract_id=contract_id,
        package_type=HoursPackageType.MONTHLY,
        hours=10.0,
        added_by=added_by,
    )

    assert event.contract_id == contract_id
    assert event.package_type == HoursPackageType.MONTHLY
    assert event.hours == 10.0
    assert event.added_by == added_by


def test_create_contract_suspended_event_success():
    """
    Событие хранит данные о приостановке договора
    """

    contract_id = uuid4()
    suspended_by = uuid4()

    event = ContractSuspended(
        contract_id=contract_id,
        reason="debt",
        suspended_by=suspended_by,
    )

    assert event.contract_id == contract_id
    assert event.reason == "debt"
    assert event.suspended_by == suspended_by


def test_create_contract_reactivated_event_success():
    """
    Событие хранит данные о возобновлении договора
    """

    contract_id = uuid4()
    reactivated_by = uuid4()

    event = ContractReactivated(contract_id=contract_id, reactivated_by=reactivated_by)

    assert event.contract_id == contract_id
    assert event.reactivated_by == reactivated_by


def test_create_contract_closed_event_success():
    """
    Событие хранит данные о закрытии договора
    """

    contract_id = uuid4()
    closed_by = uuid4()

    event = ContractClosed(contract_id=contract_id, closed_by=closed_by)

    assert event.contract_id == contract_id
    assert event.closed_by == closed_by
