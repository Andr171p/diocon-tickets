import uuid

import pytest

from src.iam.domain.vo import UserRole
from src.shared.domain.exceptions import InvariantViolationError
from src.tickets.domain.entities import Ticket
from src.tickets.domain.vo import TicketNumber, TicketStatus

# ====================== Fixtures ======================


@pytest.fixture
def ticket_id():
    return uuid.uuid4()


@pytest.fixture
def reporter_id():
    return uuid.uuid4()


@pytest.fixture
def created_by_id():
    return uuid.uuid4()


@pytest.fixture
def project_id():
    return uuid.uuid4()


@pytest.fixture
def counterparty_id():
    return uuid.uuid4()


@pytest.fixture
def sample_ticket_number():
    return TicketNumber(value="WEB-26-00000145")


# ====================== Тест кейсы ======================


def test_empty_title_raises_error(reporter_id, created_by_id, sample_ticket_number):
    with pytest.raises(ValueError, match="Title cannot be empty"):
        Ticket.create(
            ticket_number=sample_ticket_number,
            reporter_id=reporter_id,
            created_by=created_by_id,
            created_by_role=UserRole.SUPPORT_AGENT,
            title="   ",
        )


class TestCreate:
    """
    Тесты для создания тикета
    """

    def test_create_ticket_minimal_success(self, reporter_id, created_by_id, sample_ticket_number):
        ticket = Ticket.create(
            ticket_number=sample_ticket_number,
            reporter_id=reporter_id,
            created_by=created_by_id,
            created_by_role=UserRole.SUPPORT_AGENT,
            title="Проблема с авторизацией",
        )

        assert ticket.reporter_id == reporter_id
        assert ticket.created_by == created_by_id
        assert ticket.created_by_role == UserRole.SUPPORT_AGENT
        assert ticket.title == "Проблема с авторизацией"
        assert ticket.status == TicketStatus.NEW
        assert ticket.number == sample_ticket_number
        assert len(ticket.history) == 1
        assert ticket.history[0].action == "ticket_created"

    def test_create_customer_ticket_requires_counterparty(
        self, reporter_id, created_by_id, sample_ticket_number
    ):
        with pytest.raises(InvariantViolationError) as exc:
            Ticket.create(
                ticket_number=sample_ticket_number,
                reporter_id=reporter_id,
                created_by=created_by_id,
                created_by_role=UserRole.CUSTOMER,
                title="Не работает оплата",
                counterparty_id=None,
            )

        assert "must be linked to a counterparty" in str(exc.value).lower()

    def test_create_ticket_with_project_and_counterparty(
        reporter_id, created_by_id, sample_ticket_number, project_id, counterparty_id
    ):
        ticket = Ticket.create(
            ticket_number=sample_ticket_number,
            reporter_id=reporter_id,
            created_by=created_by_id,
            created_by_role=UserRole.SUPPORT_AGENT,
            title="Задача",
            project_id=project_id,
            counterparty_id=counterparty_id,
        )

        assert ticket.project_id == project_id
        assert ticket.counterparty_id == counterparty_id
