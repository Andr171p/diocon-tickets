from decimal import Decimal
from uuid import uuid4

import pytest

from src.iam.domain.vo import UserRole
from src.iam.infra.repos import SqlUserRepository
from src.iam.schemas import CurrentUser
from src.projects.domain.entities import Project
from src.projects.domain.services import ProjectAccessService
from src.projects.domain.vo import ProjectRole
from src.projects.infra.repos import SqlMembershipRepository, SqlProjectRepository
from src.iam.domain.exceptions import PermissionDeniedError
from src.shared.domain.exceptions import InvalidStateError, NotFoundError
from src.shared.infra.events import EventBus
from src.tasks.domain.entities import Task
from src.tasks.domain.vo import TaskNumber, TaskStatus
from src.tasks.infra.repos import SqlTaskRepository
from src.tasks.schemas import TaskCreate, TaskEdit
from src.tasks.services.task import TaskService
from src.tickets.domain.entities import Ticket
from src.tickets.domain.vo import Priority, TicketNumber
from src.tickets.infra.repos import SqlTicketRepository


@pytest.fixture
def task_repo(session):
    return SqlTaskRepository(session)


@pytest.fixture
def ticket_repo(session):
    return SqlTicketRepository(session)


@pytest.fixture
def membership_repo(session):
    return SqlMembershipRepository(session)


@pytest.fixture
def project_repo(session):
    return SqlProjectRepository(session)


@pytest.fixture
def user_repo(session):
    return SqlUserRepository(session)


@pytest.fixture
def project_access_service(membership_repo):
    return ProjectAccessService(membership_repo)


@pytest.fixture
def event_publisher():
    return EventBus(max_queue_size=10)


@pytest.fixture
def task_service(session, task_repo, ticket_repo, user_repo, project_repo, project_access_service, event_publisher):
    return TaskService(
        session=session,
        task_repo=task_repo,
        ticket_repo=ticket_repo,
        user_repo=user_repo,
        project_repo=project_repo,
        project_access_service=project_access_service,
        event_publisher=event_publisher
    )


@pytest.fixture
def current_support_manager():
    return CurrentUser(
        user_id=uuid4(),
        email=f"task-service-manager-{uuid4()}@example.com",
        role=UserRole.SUPPORT_MANAGER,
        counterparty_id=None,
    )


def make_project(owner_id=None) -> Project:
    user_id = owner_id or uuid4()

    return Project.create(
        name=f"Task Service Project {uuid4()}",
        key=f"TS{uuid4().hex[:6].upper()}",
        created_by=user_id,
        description="Project for task service integration test",
    )


def make_ticket(*, project_id=None, created_by=None) -> Ticket:
    user_id = created_by or uuid4()

    return Ticket.create(
        ticket_number=TicketNumber(f"TS-26-{uuid4().int % 10**8:08d}"),
        reporter_id=user_id,
        created_by=user_id,
        created_by_role=UserRole.SUPPORT_MANAGER,
        title=f"Task service ticket {uuid4()}",
        description="Ticket for task service integration test",
        project_id=project_id,
        priority=Priority.MEDIUM,
    )


def make_task_create(**overrides) -> TaskCreate:
    data = {
        "ticket_id": None,
        "project_id": None,
        "title": f"Task service task {uuid4()}",
        "description": "Task created through TaskService",
        "priority": Priority.MEDIUM,
        "story_points": None,
        "assignee_id": None,
        "reviewer_id": None,
        "estimated_hours": Decimal("2"),
        "due_date": None,
        "tags": [],
        "mark_as_todo": False,
    }
    data.update(overrides)
    return TaskCreate(**data)


@pytest.mark.asyncio
async def test_create_task_with_missing_ticket_returns_404(task_service, current_support_manager):
    """
    Проверка TaskService.create: если передан ticket_id, которого нет в бд,
    сервис должен вернуть NotFoundError.
    Данные: случайный ticket_id без сохранённого тикета.
    """

    missing_ticket_id = uuid4()
    data = make_task_create(ticket_id=missing_ticket_id)
    
    with pytest.raises(NotFoundError, match=f"Ticket with ID {missing_ticket_id} not found"):
        await task_service.create(data, current_user=current_support_manager)


@pytest.mark.asyncio
async def test_create_task_with_missing_project_returns_404(task_service, current_support_manager):
    """
    Проверка TaskService.create: если передан project_id, которого нет в бд,
    сервис должен вернуть NotFoundError.
    Данные: случайный project_id без сохранённого проекта.
    """

    missing_project_id = uuid4()
    data = make_task_create(project_id=missing_project_id)
    
    with pytest.raises(NotFoundError, match=f"Project with ID {missing_project_id} not found"):
        await task_service.create(data, current_user=current_support_manager)


@pytest.mark.asyncio
async def test_create_task_with_missing_project_returns_404(task_service, current_support_manager):
    """
    Проверка TaskService.create: если передан project_id, которого нет в БД,
    сервис должен вернуть NotFoundError.
    Данные: случайный project_id без сохранённого проекта.
    """

    missing_project_id = uuid4()
    data = make_task_create(project_id=missing_project_id)

    with pytest.raises(NotFoundError, match=f"Project with ID {missing_project_id} not found"):
        await task_service.create(data, current_user=current_support_manager)


@pytest.mark.asyncio
async def test_create_task_with_ticket_and_mismatched_project_returns_409(session, task_service, ticket_repo, project_repo, current_support_manager):
    """
    Проверка TaskService.create: если тикет принадлежит одному проекту,
    а в данных создания задачи передан другой project_id, сервис должен
    запретить создание задачи.
    Данные: два проекта и тикет, привязанный только к первому проекту.
    """

    ticket_project = make_project(owner_id=current_support_manager.user_id)
    another_project = make_project(owner_id=current_support_manager.user_id)

    ticket = make_ticket(
        project_id=ticket_project.id,
        created_by=current_support_manager.user_id,
    )

    await project_repo.create(ticket_project)
    await project_repo.create(another_project)
    await ticket_repo.create(ticket)
    await session.commit()

    data = make_task_create(
        ticket_id=ticket.id,
        project_id=another_project.id,
    )

    with pytest.raises(InvalidStateError, match="Project mismatch with ticket"):
        await task_service.create(data, current_user=current_support_manager)


@pytest.mark.asyncio
async def test_create_task_with_project_creates_project_number(session, task_service, task_repo, project_repo, membership_repo, current_support_manager):
    """
    Проверка TaskService.create: если задача создаётся внутри проекта,
    сервис должен создать номер задачи с ключом проекта и сохранить задачу в БД.
    Данные: проект, membership текущего пользователя и TaskCreate с project_id.
    """

    project = make_project(owner_id=current_support_manager.user_id)

    membership = project.create_membership(
        user_id=current_support_manager.user_id,
        project_role=ProjectRole.MANAGER,
        created_by=current_support_manager.user_id
    )

    await project_repo.create(project)
    await membership_repo.create(membership)
    await session.commit()

    data = make_task_create(
        project_id=project.id,
        mark_as_todo=True,
    )

    response = await task_service.create(data, current_user=current_support_manager)
    created_task = await task_repo.read(response.id)

    assert response.project_id == project.id
    assert response.number.startswith(f"{project.key}-")
    assert response.status == TaskStatus.TODO

    assert created_task is not None
    assert created_task.project_id == project.id
    assert created_task.number.value == response.number
    assert created_task.status == TaskStatus.TODO

    assert created_task is not None
    assert created_task.project_id == project.id
    assert created_task.number.value == response.number
    assert created_task.status == TaskStatus.TODO


@pytest.mark.asyncio
async def test_create_task_denies_customer_user(task_service):
    """
    Проверяем TaskService.create: пользователь с ролью CUSTOMER не может
    создавать задачи.
    Данные: CurrentUser с ролью CUSTOMER и валидный TaskCreate без проекта и тикета.
    """

    customer_user = CurrentUser(
        user_id=uuid4(),
        email=f"task-service-customer-{uuid4()}@example.com",
        role=UserRole.CUSTOMER,
        counterparty_id=uuid4(),
    )

    data = make_task_create()

    with pytest.raises(PermissionDeniedError):
        await task_service.create(data, current_user=customer_user)


@pytest.mark.asyncio
async def test_edit_task_denies_not_creator_or_assignee(session, task_service, task_repo):
    """
    Проверяем TaskService.editЖ support-пользователь не может редактировать задачу,
    если он не является ни создатеелем, ни испольнителем.
    Данные: задача, созданная одним пользователем, и другой support-agent. 
    """

    creator_id = uuid4()
    assignee_id = uuid4()

    task = Task(
        number=TaskNumber(f"TASK-{uuid4().int % 10**8:08d}"),
        title=f"Task service edit denied {uuid4()}",
        description="Task for edit permission integration test",
        status=TaskStatus.BACKLOG,
        priority=Priority.MEDIUM,
        assignee_id=assignee_id,
        actual_hours=Decimal(0),
        created_by=creator_id,
    )

    await task_repo.create(task)
    await session.commit()

    another_support_user = CurrentUser(
        user_id=uuid4(),
        email=f"task-service-editor-{uuid4()}@example.com",
        role=UserRole.SUPPORT_AGENT,
        counterparty_id=None,
    )

    data = TaskEdit(
        title="Updated title",
        description="Updated description",
        priority=Priority.HIGH,
        story_points=5,
        estimated_hours=4,
        due_date=None,
    )

    with pytest.raises(PermissionDeniedError):
        await task_service.edit(
            task_id=task.id,
            data=data,
            current_user=another_support_user,
        )

    unchanged_task = await task_repo.read(task.id)

    assert unchanged_task is not None
    assert unchanged_task.title == task.title
    assert unchanged_task.description == task.description
    assert unchanged_task.priority == Priority.MEDIUM
