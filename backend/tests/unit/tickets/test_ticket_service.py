from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.crm.domain.entities import Counterparty
from src.crm.domain.vo import CounterpartyType, Inn, Kpp, Phone
from src.iam.domain.vo import UserRole
from src.tickets.domain.entities import Project
from src.tickets.domain.vo import ProjectRole, TicketPriority
from src.tickets.schemas import Tag, TicketCreate
from src.tickets.services import TicketService


@pytest.fixture
def mock_session():
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def ticket_service(
        mock_session,
        mock_ticket_repo,
        mock_project_repo,
        mock_counterparty_repo,
        event_publisher,
):
    return TicketService(
        session=mock_session,
        ticket_repo=mock_ticket_repo,
        project_repo=mock_project_repo,
        counterparty_repo=mock_counterparty_repo,
        event_publisher=event_publisher,
    )


@pytest.fixture
async def sample_counterparty(mock_counterparty_repo):
    counterparty = Counterparty(
        counterparty_type=CounterpartyType.LEGAL_ENTITY,
        name="ООО Ромашка",
        legal_name="Общество с ограниченной ответственностью «Ромашка»",
        inn=Inn("7707083893"),
        kpp=Kpp("773301001"),
        phone=Phone("+79991234567"),
        email="info@romashka.ru",
    )
    await mock_counterparty_repo.create(counterparty)
    return counterparty


@pytest.fixture
def user_id():
    return uuid4()


@pytest.fixture
def owner_id():
    return uuid4()


@pytest.fixture
async def sample_project(mock_project_repo, sample_counterparty, owner_id, user_id):
    project = Project.create(
        name="Test Project",
        key="TEST",
        owner_id=owner_id,
        created_by=uuid4(),
        description="Test description",
        counterparty_id=sample_counterparty.id,
    )
    project.add_member(
        user_id=user_id,
        project_role=ProjectRole.MEMBER,
        added_by=owner_id,
        added_by_role=UserRole.CUSTOMER_ADMIN,
    )
    await mock_project_repo.create(project)
    return project


class TestCreateTicket:
    """
    Тестирование метода для создания тикета
    """

    @pytest.mark.asyncio
    async def test_create_internal_and_exists_success(
            self, ticket_service, mock_ticket_repo
    ):
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

        existing_ticket = await mock_ticket_repo.read(response.id)
        assert existing_ticket is not None
        assert existing_ticket.number.value.startswith("INT-")

    @pytest.mark.asyncio
    async def test_create_for_counterparty_success(
            self, ticket_service, sample_counterparty
    ):
        # 1. Формирование входных параметров
        created_by = uuid4()
        created_by_role = UserRole.SUPPORT_AGENT
        data = TicketCreate(
            reporter_id=uuid4(),
            title="Ошибка при авторизации",
            description="Пользователи не могут авторизоваться под своей учёткой",
            priority=TicketPriority.HIGH,
            tags=[Tag(name="Инцидент", color="#f54242"), Tag(name="Баг", color="#42f554")],
            counterparty_id=sample_counterparty.id,
        )

        # 2. Создание тикета
        response = await ticket_service.create(data, created_by, created_by_role)

        assert response.id is not None
        assert not response.number.startswith("INT-")
        assert response.number.startswith("OOOROMASHK-")
        assert response.counterparty_id == sample_counterparty.id
        assert response.project_id is None

    @pytest.mark.asyncio
    async def test_create_in_project_by_owner_success(
            self, ticket_service, sample_project, owner_id
    ):
        # 1. Формирование входных параметров
        created_by_role = UserRole.CUSTOMER_ADMIN
        data = TicketCreate(
            reporter_id=uuid4(),
            title="Ошибка при авторизации",
            description="Пользователи не могут авторизоваться под своей учёткой",
            priority=TicketPriority.HIGH,
            tags=[Tag(name="Инцидент", color="#f54242"), Tag(name="Баг", color="#42f554")],
            project_id=sample_project.id,
        )

        # 2. Создание тикета
        response = await ticket_service.create(data, owner_id, created_by_role)

        assert response.id is not None
        assert response.number.startswith(f"{sample_project.key}-")
        assert response.counterparty_id == sample_project.counterparty_id
        assert response.project_id == sample_project.id

    @pytest.mark.asyncio
    async def test_create_specify_project_and_counterparty_raises_error(
            self, ticket_service
    ):
        created_by = uuid4()
        created_by_role = UserRole.CUSTOMER_ADMIN
        data = TicketCreate(
            reporter_id=uuid4(),
            title="Ошибка при авторизации",
            description="Пользователи не могут авторизоваться под своей учёткой",
            priority=TicketPriority.HIGH,
            tags=[Tag(name="Инцидент", color="#f54242"), Tag(name="Баг", color="#42f554")],
            project_id=uuid4(),
            counterparty_id=uuid4(),
        )

        with pytest.raises(
                ValueError, match="Only one of the project or counterparty must be specified"
        ):
            await ticket_service.create(data, created_by, created_by_role)
