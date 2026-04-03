import uuid

import pytest

from src.shared.utils.time import current_datetime
from src.tickets.domain.vo import TicketNumber


def test_create_internal_ticket_number():
    ticket_id = uuid.uuid4()

    ticket_number = TicketNumber.create(ticket_id=ticket_id, counterparty_name=None)
    excepted_number_length = 15

    assert isinstance(ticket_number, TicketNumber)
    assert ticket_number.value.startswith("INT-")
    assert len(ticket_number.value) == excepted_number_length
    assert ticket_number.is_internal is True
    assert ticket_number.prefix == "INT"


def test_create_ticket_number_with_counterparty():
    ticket_id = uuid.uuid4()

    ticket_number = TicketNumber.create(ticket_id=ticket_id, counterparty_name="Ромашка")

    assert ticket_number.value.startswith("РОМ-")
    assert ticket_number.prefix == "РОМ"
    assert ticket_number.is_internal is False


def test_create_ticket_number_with_short_counterparty_name():
    ticket_id = uuid.uuid4()

    ticket_number = TicketNumber.create(ticket_id=ticket_id, counterparty_name="Я")

    assert ticket_number.prefix == "ЯXX"


def test_create_ticket_number_with_long_counterparty_name():
    ticket_id = uuid.uuid4()

    ticket_number = TicketNumber.create(
        ticket_id=ticket_id, counterparty_name="Общество с ограниченной ответственностью Ромашка"
    )

    assert ticket_number.prefix == "ОБЩ"


@pytest.mark.parametrize("counterparty_name", ["", None, "   "])
def test_create_internal_ticket_when_no_counterparty_name(counterparty_name):
    ticket_id = uuid.uuid4()

    ticket_number = TicketNumber.create(ticket_id=ticket_id, counterparty_name=counterparty_name)

    assert ticket_number.is_internal is True
    assert ticket_number.prefix == "INT"


def test_ticket_number_properties():
    ticket_id = uuid.uuid4()
    ticket_number = TicketNumber.create(
        ticket_id=ticket_id,
        counterparty_name="Яндекс"
    )

    max_year_short = 99
    number_sequence = 8

    assert ticket_number.prefix == "ЯНД"
    assert isinstance(ticket_number.year_short, int)
    assert 0 <= ticket_number.year_short <= max_year_short
    assert len(ticket_number.sequence) == number_sequence
    assert ticket_number.sequence.isdigit()


def test_invalid_ticket_number_raises_error():
    with pytest.raises(ValueError, match="Invalid ticket number format"):
        TicketNumber(value="РОМ-26-1234567")

    with pytest.raises(ValueError, match="Invalid ticket number format"):
        TicketNumber(value="ROM-2026-12345678")

    with pytest.raises(ValueError, match="Ticket number cannot be empty"):
        TicketNumber(value="")


def test_str_and_repr():
    ticket_id = uuid.uuid4()
    ticket_number = TicketNumber.create(ticket_id=ticket_id, counterparty_name="Сбер")

    assert str(ticket_number) == ticket_number.value
    assert repr(ticket_number).startswith("TicketNumber(")
    assert ticket_number.value in repr(ticket_number)


def test_equality():
    ticket_id = uuid.uuid4()
    number1 = TicketNumber.create(ticket_id=ticket_id, counterparty_name="Ромашка")
    number2 = TicketNumber(value=number1.value)

    assert number1 == number2
    assert number1 != "РОМ-26-99999999"


def test_year_changes_correctly():
    ticket_id = uuid.uuid4()
    current_year_short = current_datetime().year % 100

    ticket_number = TicketNumber.create(ticket_id=ticket_id, counterparty_name="Тест")

    assert ticket_number.year_short == current_year_short


@pytest.mark.parametrize(
    "invalid_number",
    [
        "РОМ-26-1234567",           # 7 цифр вместо 8
        "РОМ-2026-000123",        # год 4 цифры
        "РОМ26-000123",           # без дефиса
        "РОМ-26-000123455",         # 9 цифр
        "Р-26-000123",            # префикс короче 3
    ]
)
def test_invalid_formats_raise_error(invalid_number):
    with pytest.raises(ValueError, match="Invalid ticket number format"):
        TicketNumber(value=invalid_number)
