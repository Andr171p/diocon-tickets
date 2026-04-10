from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.iam.domain.vo import UserRole
from src.shared.infra.events import EventBus
from src.tickets.domain.vo import TicketPriority
from src.tickets.schemas import TicketCreate
from src.tickets.services import TicketService


@pytest.fixture
def mock_session():
    session = AsyncMock(spec=AsyncSession)
    session.begin.return_value.__aenter__ = AsyncMock()
    session.begin.return_value.__aexit__ = AsyncMock()
    return session


@pytest.fixture
def event_bus():
    return EventBus(max_queue_size=10)


@pytest.fixture
def ticket_service(
        mock_session,
        mock_ticket_repo,
        mock_project_repo,
        mock_counterparty_repo,
        event_bus,
):
    return TicketService(
        session=mock_session,
        ticket_repo=mock_ticket_repo,
        project_repo=mock_project_repo,
        counterparty_repo=mock_counterparty_repo,
        event_publisher=event_bus,
    )


class TestCreateTicket:
    """
    Тестирование метода для создания тикета
    """

    async def test_create_internal_ticket_success(self, ticket_service, mock_ticket_repo):
        created_by = uuid4()
        data = TicketCreate(
            reporter_id=uuid4(),
            title="Internal issue",
            description="Some description",
            priority=TicketPriority.MEDIUM,
            tags=[],
        )

        response = await ticket_service.create(data, created_by, UserRole.ADMIN)

        assert response.id is not None
        assert response.title == data.title
        assert response.project_id is None
        assert response.counterparty_id is None

        ticket_in_repo = await mock_ticket_repo.read(response.id)
        assert ticket_in_repo is not None
        assert ticket_in_repo.number.value.startswith("INT-")
