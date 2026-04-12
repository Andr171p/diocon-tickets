import uuid

import pytest

from src.iam.domain.exceptions import PermissionDeniedError
from src.iam.domain.vo import UserRole
from src.shared.domain.exceptions import InvariantViolationError
from src.tickets.domain.entities import Ticket
from src.tickets.domain.vo import TicketNumber, TicketPriority, TicketStatus

# ====================== Fixtures ======================


@pytest.fixture
def ticket_id():
    return uuid.uuid4()


@pytest.fixture
def reporter_id():
    return uuid.uuid4()


@pytest.fixture
def support_agent_id():
    return uuid.uuid4()


@pytest.fixture
def customer_admin_id():
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


@pytest.fixture
def ticket_in_new(reporter_id, support_agent_id, sample_ticket_number):
    return Ticket.create(
        ticket_number=sample_ticket_number,
        reporter_id=reporter_id,
        created_by=support_agent_id,
        created_by_role=UserRole.SUPPORT_AGENT,
        title="Тестовый тикет",
        description="Описание",
        priority=TicketPriority.MEDIUM,
        counterparty_id=uuid.uuid4(),
    )


@pytest.fixture
def ticket_in_pending_approval(reporter_id, sample_ticket_number):
    return Ticket.create(
        ticket_number=sample_ticket_number,
        reporter_id=reporter_id,
        created_by=reporter_id,
        created_by_role=UserRole.CUSTOMER,
        title="Тестовый тикет от клиента",
        description="Описание",
        priority=TicketPriority.HIGH,
        counterparty_id=uuid.uuid4(),
    )


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


class TestChangeStatus:
    """
    Тестирование изменение статуса тикета
    """

    def test_support_manager_can_do_any_transition(self, ticket_in_new):
        ticket = ticket_in_new

        allowed_transitions = [
            (TicketStatus.NEW, TicketStatus.PENDING_APPROVAL),
            (TicketStatus.NEW, TicketStatus.OPEN),
            (TicketStatus.PENDING_APPROVAL, TicketStatus.OPEN),
            (TicketStatus.OPEN, TicketStatus.IN_PROGRESS),
            (TicketStatus.IN_PROGRESS, TicketStatus.WAITING),
            (TicketStatus.IN_PROGRESS, TicketStatus.RESOLVED),
            (TicketStatus.RESOLVED, TicketStatus.CLOSED),
            (TicketStatus.CLOSED, TicketStatus.REOPENED),
        ]

        for from_status, to_status in allowed_transitions:
            ticket.status = from_status

            ticket.change_status(
                new_status=to_status,
                changed_by=uuid.uuid4(),
                changed_by_role=UserRole.SUPPORT_MANAGER,
            )
            assert ticket.status == to_status

    def test_customer_admin_can_approve_or_reject(self, ticket_in_pending_approval):
        ticket = ticket_in_pending_approval

        ticket.change_status(
            new_status=TicketStatus.OPEN,
            changed_by=uuid.uuid4(),
            changed_by_role=UserRole.CUSTOMER_ADMIN,
        )
        assert ticket.status == TicketStatus.OPEN

    def test_customer_admin_cannot_move_to_in_progress(self, ticket_in_pending_approval):
        ticket = ticket_in_pending_approval

        with pytest.raises(PermissionDeniedError):
            ticket.change_status(
                new_status=TicketStatus.IN_PROGRESS,
                changed_by=uuid.uuid4(),
                changed_by_role=UserRole.CUSTOMER_ADMIN,
            )

    def test_support_agent_cannot_approve(self, ticket_in_pending_approval):
        ticket = ticket_in_pending_approval

        with pytest.raises(PermissionDeniedError):
            ticket.change_status(
                new_status=TicketStatus.OPEN,
                changed_by=uuid.uuid4(),
                changed_by_role=UserRole.SUPPORT_AGENT,
            )

    def test_assignee_can_move_between_working_statuses(self, ticket_in_new):
        ticket = ticket_in_new
        ticket.status = TicketStatus.IN_PROGRESS
        assignee_id = uuid.uuid4()
        ticket.assigned_to = assignee_id

        valid_statuses = [TicketStatus.WAITING, TicketStatus.RESOLVED]

        for status in valid_statuses:
            ticket.change_status(
                new_status=status, changed_by=assignee_id, changed_by_role=UserRole.ASSIGNEE
            )
            assert ticket.status == status
            ticket.status = TicketStatus.IN_PROGRESS

    def test_invalid_transition_raises_error(self, ticket_in_new):
        ticket = ticket_in_new

        with pytest.raises(PermissionDeniedError, match="Not allowed status transition"):
            ticket.change_status(
                new_status=TicketStatus.RESOLVED,
                changed_by=uuid.uuid4(),
                changed_by_role=UserRole.SUPPORT_AGENT,
            )

    def test_close_ticket_sets_closed_at(self, ticket_in_new):
        ticket = ticket_in_new
        ticket.status = TicketStatus.RESOLVED

        ticket.change_status(
            new_status=TicketStatus.CLOSED,
            changed_by=uuid.uuid4(),
            changed_by_role=UserRole.SUPPORT_MANAGER,
        )

        assert ticket.status == TicketStatus.CLOSED
        assert ticket.closed_at is not None

    def test_customer_can_only_reopen_closed_ticket(self, ticket_in_new):
        ticket = ticket_in_new
        ticket.status = TicketStatus.CLOSED

        ticket.change_status(
            new_status=TicketStatus.REOPENED,
            changed_by=uuid.uuid4(),
            changed_by_role=UserRole.CUSTOMER,
        )

        assert ticket.status == TicketStatus.REOPENED

        ticket.status = TicketStatus.CLOSED
        with pytest.raises(PermissionDeniedError):
            ticket.change_status(
                new_status=TicketStatus.IN_PROGRESS,
                changed_by=uuid.uuid4(),
                changed_by_role=UserRole.CUSTOMER,
            )

    def test_support_manager_can_skip_pending_approval(self, ticket_in_new):
        ticket = ticket_in_new

        ticket.change_status(
            new_status=TicketStatus.OPEN,
            changed_by=uuid.uuid4(),
            changed_by_role=UserRole.SUPPORT_MANAGER,
        )
        assert ticket.status == TicketStatus.OPEN

    def test_customer_admin_can_only_approve_from_pending(self, ticket_in_pending_approval):
        ticket = ticket_in_pending_approval

        ticket.change_status(
            new_status=TicketStatus.OPEN,
            changed_by=uuid.uuid4(),
            changed_by_role=UserRole.CUSTOMER_ADMIN,
        )
        assert ticket.status == TicketStatus.OPEN

        with pytest.raises(PermissionDeniedError):
            ticket.change_status(
                new_status=TicketStatus.IN_PROGRESS,
                changed_by=uuid.uuid4(),
                changed_by_role=UserRole.CUSTOMER_ADMIN,
            )
