import uuid

import pytest

from src.iam.domain.vo import UserRole
from src.shared.domain.exceptions import InvariantViolationError
from src.tickets.domain.entities import Ticket
from src.tickets.domain.events import TicketCreated
from src.tickets.domain.vo import TicketPriority, TicketStatus


@pytest.fixture
def customer_id():
    return uuid.uuid4()


@pytest.fixture
def support_agent_id():
    return uuid.uuid4()


@pytest.fixture
def counterparty_id():
    return uuid.uuid4()


# ====================== Успешное создание ======================

def test_create_ticket_by_customer_success(customer_id, support_agent_id, counterparty_id):
    ticket = Ticket.create(
        created_by_role=UserRole.CUSTOMER,
        created_by=support_agent_id,
        reporter_id=customer_id,
        title="Проблема с оплатой",
        description="Не проходит платеж",
        priority=TicketPriority.HIGH,
        counterparty_id=counterparty_id,
        counterparty_name="Ромашка"
    )

    assert ticket.number.value.startswith("РОМ")
    assert ticket.status == TicketStatus.NEW
    assert ticket.created_by == support_agent_id
    assert ticket.counterparty_id == counterparty_id
    assert len(ticket.history) == 1
    assert ticket.history[0].action == "ticket_created"

    # Проверка события
    for event in ticket.collect_events():
        assert isinstance(event, TicketCreated)
        assert event.ticket_id == ticket.id
        assert event.priority == ticket.priority


def test_create_internal_ticket_success(support_agent_id, customer_id):
    ticket = Ticket.create(
        created_by_role=UserRole.SUPPORT_AGENT,
        created_by=support_agent_id,
        reporter_id=customer_id,
        title="Внутренняя задача по инфраструктуре",
        description="Обновить сервер",
        priority=TicketPriority.MEDIUM,
        counterparty_id=None,
        counterparty_name=None
    )

    assert ticket.counterparty_id is None
    assert ticket.status == TicketStatus.NEW

    # Проверка события
    for event in ticket.collect_events():
        assert isinstance(event, TicketCreated)
        assert event.ticket_id == ticket.id
        assert event.priority == ticket.priority


# ====================== Инварианты ======================

def test_customer_ticket_without_counterparty_raises_error(customer_id):
    with pytest.raises(InvariantViolationError) as exc:
        Ticket.create(
            created_by_role=UserRole.CUSTOMER,
            created_by=customer_id,
            reporter_id=customer_id,
            title="Проблема",
            description="Описание",
            priority=TicketPriority.LOW,
            counterparty_id=None,
        )

    assert "must be linked to a counterparty" in str(exc.value).lower()


def test_ticket_without_title_raises_error(customer_id, counterparty_id):
    with pytest.raises(ValueError, match="Title cannot be empty"):
        Ticket.create(
            created_by_role=UserRole.CUSTOMER,
            created_by=customer_id,
            reporter_id=customer_id,
            title="   ",
            description="Описание",
            priority=TicketPriority.LOW,
            counterparty_id=counterparty_id,
            counterparty_name="Ромашка"
        )


def test_ticket_incorrect_counterparty_params(customer_id, counterparty_id):
    with pytest.raises(ValueError, match="Title cannot be empty"):
        Ticket.create(
            created_by_role=UserRole.CUSTOMER,
            created_by=customer_id,
            reporter_id=customer_id,
            title="   ",
            description="Описание",
            priority=TicketPriority.LOW,
            counterparty_id=counterparty_id,
            counterparty_name="Ромашка"
        )
