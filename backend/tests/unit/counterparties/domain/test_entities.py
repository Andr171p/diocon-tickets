import uuid

import pytest

from src.counterparties.domain.entities import Counterparty
from src.counterparties.domain.vo import (
    ContactPerson,
    CounterpartyType,
    Inn,
    Kpp,
    Phone,
)
from src.iam.domain.vo import FullName
from src.shared.domain.exceptions import InvariantViolationError


@pytest.fixture
def valid_inn_legal():
    return Inn("7707083893")  # 10 цифр


@pytest.fixture
def valid_inn_ip():
    return Inn("123456789012")  # 12 цифр


@pytest.fixture
def valid_kpp():
    return Kpp("773301001")


@pytest.fixture
def valid_phone():
    return Phone("+79991234567")


@pytest.fixture
def valid_contact_person():
    return ContactPerson(
        full_name=FullName("Петрова Анна Сергеевна"),
        phone=Phone("+79991234567"),
        email="anna@example.com",
    )


# ====================== Успешное создание ======================

def test_create_legal_entity_success(valid_inn_legal, valid_kpp, valid_phone):
    counterparty = Counterparty(
        counterparty_type=CounterpartyType.LEGAL_ENTITY,
        name="ООО Ромашка",
        legal_name="Общество с ограниченной ответственностью «Ромашка»",
        inn=valid_inn_legal,
        kpp=valid_kpp,
        phone=valid_phone,
        email="info@romashka.ru",
    )

    assert counterparty.counterparty_type == CounterpartyType.LEGAL_ENTITY
    assert counterparty.is_master is True
    assert counterparty.is_slave is False


def test_create_individual_entrepreneur_success(valid_inn_ip, valid_phone):
    counterparty = Counterparty(
        counterparty_type=CounterpartyType.INDIVIDUAL_ENTREPRENEUR,
        name="Иванов Иван Иванович",
        legal_name="ИП Иванов И.И.",
        inn=valid_inn_ip,
        phone=valid_phone,
        email="ivanov@example.com",
        kpp=None,
        okpo=None,
    )

    assert counterparty.counterparty_type == CounterpartyType.INDIVIDUAL_ENTREPRENEUR


def test_create_branch_success(valid_inn_legal, valid_kpp, valid_phone):
    master_id = uuid.uuid4()

    branch = Counterparty(
        counterparty_type=CounterpartyType.BRANCH,
        name="Филиал в Санкт-Петербурге",
        legal_name="ООО Ромашка (филиал в СПб)",
        inn=valid_inn_legal,
        kpp=valid_kpp,
        phone=valid_phone,
        email="spb@romashka.ru",
        parent_id=master_id,
        is_slave=True,
    )

    assert branch.is_slave is True
    assert branch.is_master is False
    assert branch.parent_id == master_id


# ====================== Ошибки инвариантов ======================

def test_legal_entity_without_kpp_raises_error(valid_inn_legal, valid_phone):
    with pytest.raises(InvariantViolationError) as exc:
        Counterparty(
            counterparty_type=CounterpartyType.LEGAL_ENTITY,
            name="ООО Ромашка",
            legal_name="Общество с ограниченной ответственностью «Ромашка»",
            inn=valid_inn_legal,
            kpp=None,
            phone=valid_phone,
            email="info@romashka.ru",
        )

    assert "KPP required" in str(exc.value)


def test_ip_with_kpp_raises_error(valid_inn_ip, valid_kpp, valid_phone):
    with pytest.raises(InvariantViolationError) as exc:
        Counterparty(
            counterparty_type=CounterpartyType.INDIVIDUAL_ENTREPRENEUR,
            name="ИП Иванов",
            legal_name="ИП Иванов И.И.",
            inn=valid_inn_ip,
            kpp=valid_kpp,
            phone=valid_phone,
            email="ip@example.com",
        )

    assert "KPP not required" in str(exc.value)


def test_wrong_inn_length_for_legal_entity(valid_inn_ip, valid_kpp, valid_phone):
    with pytest.raises(InvariantViolationError) as exc:
        Counterparty(
            counterparty_type=CounterpartyType.LEGAL_ENTITY,
            name="ООО Ромашка",
            legal_name="Общество с ограниченной ответственностью «Ромашка»",
            inn=valid_inn_ip,
            kpp=valid_kpp,
            phone=valid_phone,
            email="info@romashka.ru",
        )

    assert "10 digits" in str(exc.value)


def test_wrong_inn_length_for_ip(valid_inn_legal, valid_phone):
    with pytest.raises(InvariantViolationError) as exc:
        Counterparty(
            counterparty_type=CounterpartyType.INDIVIDUAL_ENTREPRENEUR,
            name="ИП Иванов",
            legal_name="ИП Иванов И.И.",
            inn=valid_inn_legal,
            phone=valid_phone,
            email="ip@example.com",
        )

    assert "12 digits" in str(exc.value)


def test_slave_without_parent_id_raises_error(valid_inn_legal, valid_kpp, valid_phone):
    with pytest.raises(InvariantViolationError) as exc:
        Counterparty(
            counterparty_type=CounterpartyType.BRANCH,
            name="Филиал",
            legal_name="Филиал в СПб",
            inn=valid_inn_legal,
            kpp=valid_kpp,
            phone=valid_phone,
            email="branch@example.com",
            is_slave=True,
            parent_id=None,
        )

    assert "must have a link to the parent ID" in str(exc.value)


# ====================== Свойства ======================

def test_is_master_and_is_slave_properties():
    master = Counterparty(
        counterparty_type=CounterpartyType.LEGAL_ENTITY,
        name="Головная компания",
        legal_name="Головная компания",
        inn=Inn("7707083893"),
        kpp=Kpp("773301001"),
        phone=Phone("+79991234567"),
        email="head@company.ru",
    )

    assert master.is_master is True
    assert master.is_slave is False

    slave = Counterparty(
        counterparty_type=CounterpartyType.BRANCH,
        name="Филиал",
        legal_name="Филиал",
        inn=Inn("7707083893"),
        kpp=Kpp("773301001"),
        phone=Phone("+79991234567"),
        email="branch@company.ru",
        parent_id=uuid.uuid4(),
        is_slave=True,
    )

    assert slave.is_master is False
    assert slave.is_slave is True


# ====================== Дополнительные тесты ======================

"""
def test_foreign_legal_entity_allows_any_inn_length():
    foreign = Counterparty(
        counterparty_type=CounterpartyType.FOREIGN_LEGAL_ENTITY,
        name="Foreign Company Ltd",
        legal_name="Foreign Company Ltd",
        inn=Inn("123456"),
        phone=Phone("+441234567890"),
        email="foreign@company.com",
    )

    assert foreign.counterparty_type == CounterpartyType.FOREIGN_LEGAL_ENTITY
"""
