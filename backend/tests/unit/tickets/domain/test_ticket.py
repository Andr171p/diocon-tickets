from uuid import UUID, uuid4

import pytest

from src.iam.domain.exceptions import PermissionDeniedError
from src.shared.domain.exceptions import InvariantViolationError
from src.tickets.domain.entities import Tag, Ticket, UserRole
from src.tickets.domain.vo import TicketPriority, TicketStatus


@pytest.fixture
def any_uuid() -> UUID:
    return uuid4()


@pytest.fixture
def internal_user_id(any_uuid) -> UUID:
    return any_uuid


@pytest.fixture
def customer_id(any_uuid) -> UUID:
    return any_uuid


@pytest.fixture
def support_agent_id(any_uuid) -> UUID:
    return any_uuid


@pytest.fixture
def counterparty_id(any_uuid) -> UUID:
    return any_uuid


@pytest.fixture
def counterparty_name() -> str:
    return "РОМАШКА"


@pytest.fixture
def ticket_data(internal_user_id, counterparty_id, counterparty_name):
    return {
        "created_by_role": UserRole.ADMIN,
        "created_by": internal_user_id,
        "reporter_id": internal_user_id,
        "title": "Тестовый тикет",
        "description": "Описание",
        "priority": TicketPriority.MEDIUM,
        "counterparty_name": counterparty_name,
        "counterparty_id": counterparty_id,
        "tags": [Tag(name="Инцидент")],
    }


@pytest.fixture
def created_ticket(ticket_data) -> Ticket:
    return Ticket.create(**ticket_data)


class TestTicketCreate:
    """
    Тестирование создание тикета
    """

    def test_create_should_succeed_with_valid_internal_data(self, internal_user_id):
        ticket = Ticket.create(
            created_by_role=UserRole.ADMIN,
            created_by=internal_user_id,
            reporter_id=internal_user_id,
            title="Внутренний тикет",
            description="Детальное описание",
            priority=TicketPriority.HIGH,
        )
        assert ticket.id is not None
        assert ticket.status == TicketStatus.NEW
        assert ticket.counterparty_id is None
        assert ticket.number.prefix == "INT"
        assert len(ticket.history) == 1
        assert ticket.history[0].action == "ticket_created"

    def test_create_should_succeed_with_counterparty(
            self, internal_user_id, counterparty_id, counterparty_name
    ):
        ticket = Ticket.create(
            created_by_role=UserRole.CUSTOMER,
            created_by=internal_user_id,
            reporter_id=internal_user_id,
            title="Клиентский тикет",
            description="Описание проблемы",
            priority=TicketPriority.LOW,
            counterparty_name=counterparty_name,
            counterparty_id=counterparty_id,
        )
        assert ticket.counterparty_id == counterparty_id
        assert ticket.number.prefix == counterparty_name[:3].upper()

    def test_create_should_raise_error_when_title_empty(self, internal_user_id):
        with pytest.raises(ValueError, match="Title cannot be empty"):
            Ticket.create(
                created_by_role=UserRole.ADMIN,
                created_by=internal_user_id,
                reporter_id=internal_user_id,
                title="   ",
                description="Описание",
                priority=TicketPriority.MEDIUM,
            )

    def test_create_should_raise_error_when_customer_without_counterparty(self, internal_user_id):
        with pytest.raises(
                InvariantViolationError,
                match="Customer-created ticket must be linked to a counterparty"
        ):
            Ticket.create(
                created_by_role=UserRole.CUSTOMER,
                created_by=internal_user_id,
                reporter_id=internal_user_id,
                title="No counterparty",
                description="desc",
                priority=TicketPriority.MEDIUM,
                counterparty_name=None,
                counterparty_id=None,
            )

    def test_create_should_raise_error_when_mismatched_counterparty_params(
            self, internal_user_id
    ):
        with pytest.raises(
                ValueError, match="Both counterparty_id and counterparty_name must be"
        ):
            Ticket.create(
                created_by_role=UserRole.ADMIN,
                created_by=internal_user_id,
                reporter_id=internal_user_id,
                title="Mismatch",
                description="desc",
                priority=TicketPriority.MEDIUM,
                counterparty_name="NAME",
                counterparty_id=None,  # missing
            )


class TestTicketAssign:
    """
    Тестирование назначение тикета
    """

    def test_assign_to_should_succeed_when_status_allowed(self, created_ticket, support_agent_id):
        created_ticket.status = TicketStatus.OPEN
        created_ticket.assign_to(
            assignee_id=support_agent_id,
            assigned_by=support_agent_id,
            assigned_by_role=UserRole.SUPPORT_AGENT
        )
        assert created_ticket.assigned_to == support_agent_id
        assert created_ticket.history[-1].action == "assigned"
        assert created_ticket.history[-1].new_value == str(support_agent_id)

    def test_assign_to_should_raise_permission_error_when_wrong_role(self, created_ticket):
        created_ticket.status = TicketStatus.OPEN
        with pytest.raises(PermissionDeniedError, match="Only support staff can assign tickets"):
            created_ticket.assign_to(
                assignee_id=uuid4(),
                assigned_by=uuid4(),
                assigned_by_role=UserRole.CUSTOMER
            )

    def test_assign_to_should_raise_error_when_status_not_allowed(
            self, created_ticket, support_agent_id
    ):
        assert created_ticket.status == TicketStatus.NEW
        with pytest.raises(PermissionDeniedError):
            created_ticket.assign_to(
                assignee_id=support_agent_id,
                assigned_by=support_agent_id,
                assigned_by_role=UserRole.SUPPORT_AGENT
            )

    def test_assign_to_should_overwrite_previous_assignee(self, created_ticket, support_agent_id):
        created_ticket.status = TicketStatus.OPEN
        first_assignee = uuid4()
        created_ticket.assign_to(first_assignee, support_agent_id, UserRole.SUPPORT_AGENT)
        assert created_ticket.assigned_to == first_assignee

        second_assignee = uuid4()
        created_ticket.assign_to(second_assignee, support_agent_id, UserRole.SUPPORT_AGENT)
        assert created_ticket.assigned_to == second_assignee

        # Проверяем, что в истории сохранились оба назначения
        excepted_history_entries = 2
        assign_entries = [entry for entry in created_ticket.history if entry.action == "assigned"]
        assert len(assign_entries) == excepted_history_entries
        assert assign_entries[1].old_value == str(first_assignee)
        assert assign_entries[1].new_value == str(second_assignee)
