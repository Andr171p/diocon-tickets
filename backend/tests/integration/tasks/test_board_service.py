from decimal import Decimal
from uuid import uuid4

import pytest

from src.iam.domain.exceptions import PermissionDeniedError
from src.iam.domain.vo import UserRole
from src.iam.schemas import CurrentUser
from src.projects.domain.entities import Project
from src.projects.domain.services import ProjectAccessService
from src.projects.domain.vo import ProjectRole
from src.projects.infra.repos import SqlMembershipRepository, SqlProjectRepository
from src.shared.schemas import Pagination
from src.tasks.domain.entities import Task
from src.tasks.domain.vo import TaskNumber, TaskStatus
from src.tasks.infra.repos import SqlTaskRepository
from src.tasks.schemas import (
    AssigneeKanbanContext,
    InternalKanbanContext,
    KanbanFilters,
    MyTasksKanbanContext,
    ProjectKanbanContext,
    TicketKanbanContext,
)
from src.tasks.services.board import TaskBoardService
from src.tickets.domain.vo import Priority


@pytest.fixture
def task_repo(session):
    return SqlTaskRepository(session)


@pytest.fixture
def project_repo(session):
    return SqlProjectRepository(session)


@pytest.fixture
def membership_repo(session):
    return SqlMembershipRepository(session)


@pytest.fixture
def project_access_service(membership_repo):
    return ProjectAccessService(membership_repo)


@pytest.fixture
def task_board_service(task_repo, project_access_service):
    return TaskBoardService(
        task_repo=task_repo,
        project_access_service=project_access_service,
    )


@pytest.fixture
def current_support_manager():
    return CurrentUser(
        user_id=uuid4(),
        email=f"task-board-manager-{uuid4()}@example.com",
        role=UserRole.SUPPORT_MANAGER,
        counterparty_id=None,
    )


def make_project(owner_id=None) -> Project:
    user_id = owner_id or uuid4()

    return Project.create(
        name=f"Task Board Project {uuid4()}",
        key=f"TB{uuid4().hex[:6].upper()}",
        description="Project for task board service test",
        created_by=user_id,
    )


def make_task(
    *,
    status: TaskStatus = TaskStatus.BACKLOG,
    project_id=None,
    ticket_id=None,
    assignee_id=None,
    priority: Priority = Priority.MEDIUM,
) -> Task:
    return Task(
        number=TaskNumber(f"TASK-{uuid4().int % 10**8:08d}"),
        title=f"Board task {uuid4()}",
        description="Task for board service integration test",
        status=status,
        priority=priority,
        project_id=project_id,
        ticket_id=ticket_id,
        assignee_id=assignee_id,
        actual_hours=Decimal(0),
        created_by=uuid4(),
    )


def get_column(board, status: TaskStatus):
    return next(column for column in board.columns if column.status == status)


@pytest.mark.asyncio
async def test_get_kanban_board_project_context_returns_project_tasks(
    session,
    task_repo,
    project_repo,
    membership_repo,
    task_board_service,
    current_support_manager,
):
    """
    Проверка канбан-доски проекта: сервис должен вернуть задачи только
    выбранного проекта и разложить их по колонкам статусов.
    Данные: два проекта, задача нужного проекта и задача чужого проекта.
    """

    project = make_project(owner_id=current_support_manager.user_id)
    other_project = make_project()

    membership = project.create_membership(
        user_id=current_support_manager.user_id,
        project_role=ProjectRole.MANAGER,
        created_by=current_support_manager.user_id,
    )

    project_task = make_task(
        status=TaskStatus.TODO,
        project_id=project.id,
    )

    other_project_task = make_task(
        status=TaskStatus.TODO,
        project_id=other_project.id,
    )

    await project_repo.create(project)
    await project_repo.create(other_project)
    await membership_repo.create(membership)
    await task_repo.create(project_task)
    await task_repo.create(other_project_task)
    await session.commit()

    board = await task_board_service.get_kanban_board(
        pagination=Pagination(page=1, size=10),
        context=ProjectKanbanContext(project_id=project.id),
        filters=KanbanFilters(),
        current_user=current_support_manager,
    )

    todo_column = get_column(board, TaskStatus.TODO)
    found_ids = {task.id for task in todo_column.tasks.items}

    assert board.context.project_id == project.id
    assert project_task.id in found_ids
    assert other_project_task.id not in found_ids
    assert board.total_tasks == 1


@pytest.mark.asyncio
async def test_get_kanban_board_my_context_returns_current_user_tasks(
    session,
    task_repo,
    task_board_service,
    current_support_manager,
):
    """
    Проверяем канбан "мои задачи": сервис должен вернуть только задачи,
    назначенные на текущего пользователя.
    Данные: задача текущего пользователя и задача другого исполнителя.
    """

    my_task = make_task(
        status=TaskStatus.TODO,
        assignee_id=current_support_manager.user_id,
    )

    other_task = make_task(
        status=TaskStatus.TODO,
        assignee_id=uuid4(),
    )

    await task_repo.create(my_task)
    await task_repo.create(other_task)
    await session.commit()

    board = await task_board_service.get_kanban_board(
        pagination=Pagination(page=1, size=10),
        context=MyTasksKanbanContext(),
        filters=KanbanFilters(),
        current_user=current_support_manager,
    )

    todo_column = get_column(board, TaskStatus.TODO)
    found_ids = {task.id for task in todo_column.tasks.items}

    assert my_task.id in found_ids
    assert other_task.id not in found_ids
    assert board.total_tasks == 1


@pytest.mark.asyncio
async def test_get_kanban_board_ticket_context_returns_ticket_tasks(session, task_repo, task_board_service, current_support_manager):
    """
    Проверка канбан-доски тикета: сервис должен вернуть задачи только
    выбранного тикеты и разложить их по колонкам статусов.
    Данные: два ticket_id, задача нужного тикета и задача другого тикета.
    """

    ticket_id = uuid4()
    other_ticket_id = uuid4()

    ticket_task = make_task(
        status=TaskStatus.TODO,
        ticket_id=ticket_id,
    )

    other_ticket_task = make_task(
        status=TaskStatus.TODO,
        ticket_id=other_ticket_id,
    )

    await task_repo.create(ticket_task)
    await task_repo.create(other_ticket_task)
    await session.commit()

    board = await task_board_service.get_kanban_board(
        pagination=Pagination(page=1, size=10),
        context=TicketKanbanContext(ticket_id=ticket_id),
        filters= KanbanFilters(),
        current_user=current_support_manager,
    )

    todo_column = get_column(board, TaskStatus.TODO)
    found_ids = {task.id for task in todo_column.tasks.items}

    assert board.context.ticket_id == ticket_id
    assert ticket_task.id in found_ids
    assert other_ticket_task.id not in found_ids
    assert board.total_tasks == 1


@pytest.mark.asyncio
async def test_get_kanban_board_assignee_context_returns_assignee_tasks(session, task_repo, task_board_service, current_support_manager):
    """
    Проверка канбан-доски исполнителя: сервис должен вернуть задачи только
    выбранного испольнителя.
    Данные: assignee_id, задача этого испольнителя и задача другого исполнителя.
    """

    assignee_id = uuid4()
    other_assignee_id = uuid4()

    assignee_task = make_task(
        status=TaskStatus.TODO,
        assignee_id=assignee_id,
    )

    other_assignee_task = make_task(
        status=TaskStatus.TODO,
        assignee_id=other_assignee_id,
    )

    await task_repo.create(assignee_task)
    await task_repo.create(other_assignee_task)
    await session.commit()

    board = await task_board_service.get_kanban_board(
        pagination=Pagination(page=1, size=10),
        context=AssigneeKanbanContext(assignee_id=assignee_id),
        filters=KanbanFilters(),
        current_user=current_support_manager,
    )

    todo_column = get_column(board, TaskStatus.TODO)
    found_ids = {task.id for task in todo_column.tasks.items}

    assert board.context.assignee_id == assignee_id
    assert assignee_task.id in found_ids
    assert other_assignee_task.id not in found_ids
    assert board.total_tasks == 1


@pytest.mark.asyncio
async def test_get_kanban_board_internal_context_returns_internal_tasks(session, task_repo, task_board_service, current_support_manager):
    """
    Проверка внутренней канбан-доски: сервис должен вернуть задачи без project_id.
    Данные: внутренняя задача без project_id и проектная задача с project_id.
    """

    project_id = uuid4()

    internal_task = make_task(
        status=TaskStatus.TODO,
        project_id=None,
    )

    project_task = make_task(
        status=TaskStatus.TODO,
        project_id=project_id,
    )

    await task_repo.create(internal_task)
    await task_repo.create(project_task)
    await session.commit()

    board = await task_board_service.get_kanban_board(
        pagination=Pagination(page=1, size=10),
        context=InternalKanbanContext(),
        filters=KanbanFilters(),
        current_user=current_support_manager,
    )

    todo_column = get_column(board, TaskStatus.TODO)
    found_ids = {task.id for task in todo_column.tasks.items}

    assert board.context.type == "internal"
    assert internal_task.id in found_ids
    assert project_task.id not in found_ids
    assert board.total_tasks >= 1


@pytest.mark.asyncio
async def test_get_kanban_board_applies_priority_filter(session, task_repo, task_board_service, current_support_manager):
    """
    Проверка фильтра канбан-доски по приоритету: сервис должен вернуть только
    задачи с выбранным priority.
    Данные: две внутренние TODO-задачи с разныит приоритетами.
    """

    high_priority_task = make_task(
        status=TaskStatus.TODO,
        project_id=None,
        priority=Priority.HIGH,
    )

    low_priority_task = make_task(
        status=TaskStatus.TODO,
        project_id=None,
        priority=Priority.LOW,
    )

    await task_repo.create(high_priority_task)
    await task_repo.create(low_priority_task)
    await session.commit()

    board = await task_board_service.get_kanban_board(
        pagination=Pagination(page=1, size=10),
        context=InternalKanbanContext(),
        filters=KanbanFilters(priorities=[Priority.HIGH]),
        current_user=current_support_manager,
    )

    todo_column = get_column(board, TaskStatus.TODO)
    found_ids = {task.id for task in todo_column.tasks.items}

    assert high_priority_task.id in found_ids
    assert low_priority_task.id not in found_ids
    assert all(task.priority == Priority.HIGH for task in todo_column.tasks.items)


@pytest.mark.asyncio
async def test_get_kanban_board_project_context_denies_non_member(session, project_repo, task_board_service, current_support_manager):
    """
    Проверка доступа к канбан-доске проекта: если пользователь не состоит
    в проекте, сервис должен запретить просмотр.
    Данные: проект без membership для текущего пользователя.
    """

    project = make_project()

    await project_repo.create(project)
    await session.commit()

    with pytest.raises(PermissionDeniedError, match="Your not member of this project"):
        await task_board_service.get_kanban_board(
            pagination=Pagination(page=1, size=10),
            context=ProjectKanbanContext(project_id=project.id),
            filters=KanbanFilters(),
            current_user=current_support_manager,
        )


@pytest.mark.asyncio
async def test_get_kanban_board_denies_customer_user(task_board_service):
    """
    Проверка общего запрета просмотра канбан-доски: пользователь с ролью CUSTOMER
    не должен иметь доступ к задачам до проверки конкретного context.
    Данные: текущий пользователь с системной ролью CUSTOMER.
    """

    customer_user = CurrentUser(
        user_id=uuid4(),
        email=f"task-board-customer-{uuid4()}@example.com",
        role=UserRole.CUSTOMER,
        counterparty_id=uuid4(),
    )

    with pytest.raises(PermissionDeniedError):
        await task_board_service.get_kanban_board(
            pagination=Pagination(page=1, size=10),
            context=MyTasksKanbanContext(),
            filters=KanbanFilters(),
            current_user=customer_user,
        )


@pytest.mark.asyncio
async def test_get_kanban_board_project_context_denies_customer_project_member(session, project_repo, membership_repo, task_board_service):
    """
    Проверка доступа к канбан-доске проекта: пользователь может иметь системную
    роль support, но проектная роль CUSTOMER всё равно не даёт права смотреть задачи.
    """

    user = CurrentUser(
        user_id=uuid4(),
        email=f"task-board-project-customer-{uuid4()}@example.com",
        role=UserRole.SUPPORT_AGENT,
        counterparty_id=None,
    )

    project = make_project()

    membership = project.create_membership(
        user_id=user.user_id,
        project_role=ProjectRole.CUSTOMER,
        created_by=project.created_by,
    )

    await project_repo.create(project)
    await membership_repo.create(membership)
    await session.commit()

    with pytest.raises(PermissionDeniedError):
        await task_board_service.get_kanban_board(
            pagination=Pagination(page=1, size=10),
            context=ProjectKanbanContext(project_id=project.id),
            filters=KanbanFilters(),
            current_user=user,
        )
    