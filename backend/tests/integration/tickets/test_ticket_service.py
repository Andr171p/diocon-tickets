from uuid import uuid4

import pytest

from src.crm.domain.entities import Counterparty
from src.crm.domain.vo import CounterpartyType, Inn, Kpp, Phone
from src.crm.infra.repos import SqlCounterpartyRepository
from src.iam.domain.exceptions import PermissionDeniedError
from src.iam.domain.services import create_support
from src.iam.domain.vo import UserRole
from src.iam.infra.repos import SqlUserRepository
from src.iam.schemas import CurrentUser
from src.projects.domain.entities import Project
from src.projects.domain.services import ProjectAccessService
from src.projects.domain.vo import ProjectRole
from src.projects.infra.repos import (
    SqlMembershipRepository,
    SqlProjectRepository,
)
from src.shared.infra.events import EventBus
from src.tickets.domain.vo import (
    Priority,
    TicketStatus,
    TicketType,
)
from src.tickets.infra.repos import SqlTicketRepository
from src.tickets.schemas import TicketCreate
from src.tickets.services.ticket import TicketService


@pytest.fixture
def ticket_repo(session):
    return SqlTicketRepository(session)


@pytest.fixture
def project_repo(session):
    return SqlProjectRepository(session)


@pytest.fixture
def membership_repo(session):
    return SqlMembershipRepository(session)


@pytest.fixture
def user_repo(session):
    return SqlUserRepository(session)


@pytest.fixture
def counterparty_repo(session):
    return SqlCounterpartyRepository(session)


@pytest.fixture
def project_access_service(membership_repo):
    return ProjectAccessService(membership_repo)


@pytest.fixture
def event_publisher():
    return EventBus(max_queue_size=20)


@pytest.fixture
def ticket_service(session, ticket_repo, project_repo, project_access_service, user_repo, counterparty_repo, event_publisher):
    return TicketService(
        session=session,
        ticket_repo=ticket_repo,
        project_repo=project_repo,
        project_access_service=project_access_service,
        user_repo=user_repo,
        counterparty_repo=counterparty_repo,
        event_publisher=event_publisher,
    )


@pytest.fixture
def current_support_manager():
    return CurrentUser(
        user_id=uuid4(),
        email=f"ticket-service-manager-{uuid4()}@example.com",
        role=UserRole.SUPPORT_MANAGER,
        counterparty_id=None,
    )


def make_current_user(*, role=UserRole.SUPPORT_MANAGER, user_id=None, counterparty_id=None) -> CurrentUser:
    return CurrentUser(
        user_id=user_id or uuid4(),
        email=f"ticket-service-user-{uuid4()}@example.com",
        role=role,
        counterparty_id=counterparty_id,
    )


def make_counterparty(name="Acme") -> Counterparty:
    return Counterparty(
        counterparty_type=CounterpartyType.LEGAL_ENTITY,
        name=name,
        legal_name=f"{name} Legal {uuid4()}",
        inn=Inn(f"{uuid4().int % 10**10:010d}"),
        kpp=Kpp(f"{uuid4().int % 10**9:09d}"),
        phone=Phone("+70000000000"),
        email=f"ticket-counterparty-{uuid4()}@example.com",
        contact_persons=[],
        is_active=True,
    )


def make_project(*, owner_id=None, counterparty_id=None, key=None) -> Project:
    return Project.create(
        name=f"Ticket Service Project {uuid4()}",
        key=key or f"TS{uuid4().hex[:6].upper()}",
        description="Project for TicketService integration tests",
        counterparty_id=counterparty_id,
        created_by=owner_id or uuid4(),
    )


def make_ticket_create(*, reporter_id, **overrides) ->TicketCreate:
    data = {
        "reporter_id": reporter_id,
        "title": f"Ticket service ticket {uuid4()}",
        "description": "Ticket created through TicketService",
        "type": TicketType.SERVICE_REQUEST,
        "priority": Priority.MEDIUM,
        "project_id": None,
        "counterparty_id": None,
        "product_id": None,
        "tags": [],
    }
    data.update(overrides)
    return TicketCreate(**data)


@pytest.mark.asyncio
async def test_create_ticket_with_project_uses_project_counterparty(session, ticket_service, ticket_repo, project_repo, counterparty_repo, current_support_manager):
    """
    Проверяем создание проектного тикета: TicketService должен получить
    counterparty_id из проекта и сохранить обе связи в PostgreSQL.
    Данные: существующий контрагент и связанный с ним проект.
    """

    counterparty = make_counterparty()
    project = make_project(
        owner_id=current_support_manager.user_id,
        counterparty_id=counterparty.id,
    )

    await counterparty_repo.create(counterparty)
    await project_repo.create(project)
    await session.commit()

    response = await ticket_service.create(
        make_ticket_create(
            reporter_id=current_support_manager.user_id,
            project_id=project.id,
        ),
        current_user=current_support_manager,
    )

    saved_ticket = await ticket_repo.read(response.id)

    assert saved_ticket is not None
    assert response.project_id == project.id
    assert response.counterparty_id == counterparty.id
    assert saved_ticket.project_id == project.id
    assert saved_ticket.counterparty_id == counterparty.id
    assert response.number.startswith(f"{project.key.value}-")


@pytest.mark.asyncio
async def test_create_tickets_uses_separate_sequences_for_projects(session, ticket_service, project_repo, current_support_manager):
    """
    Проверяем генерацию номеров проектных тикетов: каждый проект должен
    использовать собственную последовательность.
    Данные: два проекта, два тикета первого проекта и один тикет второго.
    """

    first_project = make_project(
        owner_id=current_support_manager.user_id,
        key=f"PA{uuid4().hex[:4].upper()}",
    )
    second_project = make_project(
        owner_id=current_support_manager.user_id,
        key=f"PB{uuid4().hex[:4].upper()}",
    )

    await project_repo.create(first_project)
    await project_repo.create(second_project)
    await session.commit()

    first_ticket = await ticket_service.create(
        make_ticket_create(
            reporter_id=current_support_manager.user_id,
            project_id=first_project.id,
        ),
        current_user=current_support_manager,
    )

    second_ticket = await ticket_service.create(
        make_ticket_create(
            reporter_id=current_support_manager.user_id,
            project_id=first_project.id,
        ),
        current_user=current_support_manager,
    )

    other_project_ticket = await ticket_service.create(
        make_ticket_create(
            reporter_id=current_support_manager.user_id,
            project_id=second_project.id,
        ),
        current_user=current_support_manager,
    )

    assert first_ticket.number.startswith(f"{first_project.key.value}-")
    assert second_ticket.number.startswith(f"{first_project.key.value}-")
    assert other_project_ticket.number.startswith(f"{second_project.key.value}-")

    assert first_ticket.number.endswith("00000001")
    assert second_ticket.number.endswith("00000002")
    assert other_project_ticket.number.endswith("00000001")