from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from src.contracts.domain.entities import ContractHoursPackage, ServiceContract, TicketEffortEstimate
from src.contracts.domain.events import (
    ContractClosed,
    ContractPackageAdded,
    ContractReactivated,
    ContractSuspended,
    HoursConsumed,
)
from src.contracts.domain.vo import (
    ContractStatus,
    ContractType,
    EstimationMethod,
    HoursPackageType,
)
from src.shared.domain.exceptions import InvariantViolationError


@pytest.fixture
def counterparty_id():
    return uuid4()


@pytest.fixture
def created_by():
    return uuid4()


@pytest.fixture
def sample_contract(counterparty_id, created_by):
    return ServiceContract(
        contract_number="CON-001",
        counterparty_id=counterparty_id,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        total_hours=Decimal("100"),
        consumed_hours=Decimal("10"),
        status=ContractStatus.ACTIVE,
        contract_type=ContractType.PREPAID,
        created_by=created_by,
    )


def test_create_contract_hours_package_success():
    """
    Успешное создание пакета часов
    """

    package = ContractHoursPackage(
        contract_id=uuid4(),
        package_type=HoursPackageType.MONTHLY,
        hours=Decimal("20"),
        consumed_hours=Decimal("5"),
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
    )

    assert package.package_type == HoursPackageType.MONTHLY
    assert package.remaining_hours == Decimal("15")


def test_create_service_contract_success(sample_contract, counterparty_id, created_by):
    """
    Успешное создание сервисного договора
    """

    assert sample_contract.contract_number == "CON-001"
    assert sample_contract.counterparty_id == counterparty_id
    assert sample_contract.created_by == created_by
    assert sample_contract.remaining_hours == Decimal("90")
    assert sample_contract.status == ContractStatus.ACTIVE
    assert sample_contract.contract_type == ContractType.PREPAID
    assert sample_contract.packages == []


@pytest.mark.parametrize("total_hours", [Decimal("0"), Decimal("-1")])
def test_create_contract_with_not_positive_total_hours_raises_error(
    counterparty_id, created_by, total_hours
):
    """
    Общее количество часов должно быть положительным
    """

    with pytest.raises(ValueError, match="Total hours must be positive"):
        ServiceContract(
            contract_number="CON-001",
            counterparty_id=counterparty_id,
            start_date=date(2026, 1, 1),
            total_hours=total_hours,
            status=ContractStatus.ACTIVE,
            contract_type=ContractType.PREPAID,
            created_by=created_by,
        )


def test_create_contract_with_negative_consumed_hours_raises_error(counterparty_id, created_by):
    """
    Списанные часы не могут быть отрицательными
    """

    with pytest.raises(ValueError, match="Consumed hours cannot be negative"):
        ServiceContract(
            contract_number="CON-001",
            counterparty_id=counterparty_id,
            start_date=date(2026, 1, 1),
            total_hours=Decimal("10"),
            consumed_hours=Decimal("-1"),
            status=ContractStatus.ACTIVE,
            contract_type=ContractType.PREPAID,
            created_by=created_by,
        )


def test_create_contract_with_consumed_more_than_total_raises_error(counterparty_id, created_by):
    """
    Списанные часы не могут быть больше общих часов
    """

    with pytest.raises(InvariantViolationError, match="Consumed hours cannot exceed total hours"):
        ServiceContract(
            contract_number="CON-001",
            counterparty_id=counterparty_id,
            start_date=date(2026, 1, 1),
            total_hours=Decimal("10"),
            consumed_hours=Decimal("11"),
            status=ContractStatus.ACTIVE,
            contract_type=ContractType.PREPAID,
            created_by=created_by,
        )


def test_create_contract_with_end_date_before_start_date_raises_error(counterparty_id, created_by):
    """
    Дата окончания не может быть раньше даты начала
    """

    with pytest.raises(InvariantViolationError, match="End date cannot be before start date"):
        ServiceContract(
            contract_number="CON-001",
            counterparty_id=counterparty_id,
            start_date=date(2026, 2, 1),
            end_date=date(2026, 1, 1),
            total_hours=Decimal("10"),
            status=ContractStatus.ACTIVE,
            contract_type=ContractType.PREPAID,
            created_by=created_by,
        )


def test_add_package_success(sample_contract):
    """
    Добавление пакета увеличивает общие и оставшиеся часы
    """

    added_by = uuid4()

    sample_contract.add_package(
        package_type=HoursPackageType.MONTHLY,
        hours=Decimal("20"),
        start_date=date(2026, 2, 1),
        end_date=date(2026, 2, 28),
        added_by=added_by,
    )

    events = list(sample_contract.collect_events())

    assert len(sample_contract.packages) == 1
    assert sample_contract.packages[0].contract_id == sample_contract.id
    assert sample_contract.total_hours == Decimal("120")
    assert sample_contract.remaining_hours == Decimal("110")
    assert len(events) == 1
    assert isinstance(events[0], ContractPackageAdded)
    assert events[0].contract_id == sample_contract.id
    assert events[0].package_type == HoursPackageType.MONTHLY
    assert events[0].hours == 20.0
    assert events[0].added_by == added_by


@pytest.mark.parametrize("hours", [Decimal("0"), Decimal("-1")])
def test_add_package_with_not_positive_hours_raises_error(sample_contract, hours):
    """
    Пакет часов должен быть положительным
    """

    with pytest.raises(ValueError, match="Package hours must be positive"):
        sample_contract.add_package(
            package_type=HoursPackageType.MONTHLY,
            hours=hours,
            start_date=date(2026, 2, 1),
            added_by=uuid4(),
        )


def test_consume_hours_success(sample_contract):
    """
    Списание часов обновляет договор и регистрирует событие
    """

    ticket_id = uuid4()
    user_id = uuid4()

    sample_contract.consume_hours(hours=Decimal("15"), ticket_id=ticket_id, user_id=user_id)

    events = list(sample_contract.collect_events())

    assert sample_contract.consumed_hours == Decimal("25")
    assert sample_contract.remaining_hours == Decimal("75")
    assert len(events) == 1
    assert isinstance(events[0], HoursConsumed)
    assert events[0].contract_id == sample_contract.id
    assert events[0].ticket_id == ticket_id
    assert events[0].user_id == user_id
    assert events[0].hours == 15.0
    assert events[0].remaining_hours == 75.0


def test_consume_negative_hours_raises_error(sample_contract):
    """
    Нельзя списать отрицательное количество часов
    """

    with pytest.raises(ValueError, match="Hours must be positive"):
        sample_contract.consume_hours(hours=Decimal("-1"), ticket_id=uuid4(), user_id=uuid4())


def test_consume_more_than_remaining_hours_raises_error(sample_contract):
    """
    Нельзя списать больше часов, чем осталось по договору
    """

    with pytest.raises(InvariantViolationError, match="Not enough remaining hours on contract"):
        sample_contract.consume_hours(hours=Decimal("91"), ticket_id=uuid4(), user_id=uuid4())


def test_suspend_active_contract_success(sample_contract):
    """
    Активный договор можно приостановить
    """

    suspended_by = uuid4()

    sample_contract.suspend(reason="debt", suspended_by=suspended_by)

    events = list(sample_contract.collect_events())

    assert sample_contract.status == ContractStatus.SUSPENDED
    assert len(events) == 1
    assert isinstance(events[0], ContractSuspended)
    assert events[0].contract_id == sample_contract.id
    assert events[0].reason == "debt"
    assert events[0].suspended_by == suspended_by


def test_suspend_not_active_contract_do_nothing(sample_contract):
    """
    Приостанавливать можно только активный договор
    """

    sample_contract.status = ContractStatus.DRAFT
    updated_at = sample_contract.updated_at

    sample_contract.suspend(reason="debt", suspended_by=uuid4())

    assert sample_contract.status == ContractStatus.DRAFT
    assert sample_contract.updated_at == updated_at
    assert list(sample_contract.collect_events()) == []


def test_reactivate_suspended_contract_success(sample_contract):
    """
    Приостановленный договор можно возобновить
    """

    sample_contract.status = ContractStatus.SUSPENDED
    reactivated_by = uuid4()

    sample_contract.reactivate(reactivated_by=reactivated_by)

    events = list(sample_contract.collect_events())

    assert sample_contract.status == ContractStatus.ACTIVE
    assert len(events) == 1
    assert isinstance(events[0], ContractReactivated)
    assert events[0].contract_id == sample_contract.id
    assert events[0].reactivated_by == reactivated_by


def test_reactivate_not_suspended_contract_do_nothing(sample_contract):
    """
    Возобновлять можно только приостановленный договор
    """

    updated_at = sample_contract.updated_at

    sample_contract.reactivate(reactivated_by=uuid4())

    assert sample_contract.status == ContractStatus.ACTIVE
    assert sample_contract.updated_at == updated_at
    assert list(sample_contract.collect_events()) == []


def test_close_contract_success(sample_contract):
    """
    Закрытие договора меняет статус и регистрирует событие
    """

    closed_by = uuid4()

    sample_contract.close(closed_by=closed_by)

    events = list(sample_contract.collect_events())

    assert sample_contract.status == ContractStatus.COMPLETED
    assert len(events) == 1
    assert isinstance(events[0], ContractClosed)
    assert events[0].contract_id == sample_contract.id
    assert events[0].closed_by == closed_by


def test_create_ticket_effort_estimate_success():
    """
    Успешное создание оценки трудозатрат по тикету
    """

    ticket_id = uuid4()
    estimated_by = uuid4()

    estimate = TicketEffortEstimate(
        ticket_id=ticket_id,
        estimated_hours=Decimal("3.5"),
        confidence=0.87,
        method=EstimationMethod.MANUAL,
        estimated_by=estimated_by,
        notes="Нужна проверка интеграции",
    )

    assert estimate.ticket_id == ticket_id
    assert estimate.estimated_hours == Decimal("3.5")
    assert estimate.confidence == 0.87
    assert estimate.method == EstimationMethod.MANUAL
    assert estimate.estimated_by == estimated_by
    assert estimate.notes == "Нужна проверка интеграции"
