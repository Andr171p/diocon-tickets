from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from src.iam.domain.vo import UserRole
from src.iam.infra.repos import SqlUserRepository
from src.projects.domain.services import ProjectAccessService
from src.projects.infra.repos import SqlMembershipRepository, SqlProjectRepository
from src.shared.infra.events import EventBus
from src.tasks.domain.entities import Task
from src.tasks.domain.vo import TaskNumber, TaskStatus
from src.tasks.infra.handlers import on_worklog_approved
from src.tasks.infra.repos import SqlTaskRepository
from src.tasks.services.task import TaskService
from src.tickets.domain.vo import Priority
from src.tickets.infra.repos import SqlTicketRepository
from src.timetracking.domain.events import WorklogApproved


class FakeLogger:
    def __init__(self):
        self.messages = []

    def info(self, message, *args):
        self.messages.append((message, args))


@pytest.fixture
def task_repo(session):
    return SqlTaskRepository(session)


@pytest.fixture
def ticket_repo(session):
    return SqlTicketRepository(session)


@pytest.fixture
def user_repo(session):
    return SqlUserRepository(session)


@pytest.fixture
def membership_repo(session):
    return SqlMembershipRepository(session)


@pytest.fixture
def project_repo(session):
    return SqlProjectRepository(session)


@pytest.fixture
def project_access_service(membership_repo):
    return ProjectAccessService(membership_repo)


@pytest.fixture
def event_publisher():
    return EventBus(max_queue_size=10)


@pytest.fixture
def task_service(
    session,
    task_repo,
    ticket_repo,
    user_repo,
    project_repo,
    project_access_service,
    event_publisher,
):
    return TaskService(
        session=session,
        task_repo=task_repo,
        ticket_repo=ticket_repo,
        user_repo=user_repo,
        project_repo=project_repo,
        project_access_service=project_access_service,
        event_publisher=event_publisher,
    )


def make_task(*, actual_hours=Decimal(0)) -> Task:
    return Task(
        number=TaskNumber(f"TASK-{uuid4().int % 10**8:08d}"),
        title=f"Task handler task {uuid4()}",
        description="Task for worklog handler integration test",
        status=TaskStatus.BACKLOG,
        priority=Priority.MEDIUM,
        actual_hours=actual_hours,
        created_by=uuid4(),
    )


@pytest.mark.asyncio
async def test_on_worklog_approved_adds_actual_hours_to_task(session, task_repo, task_service):
    """
    Проверяем обработчик WorklogApproved: если событие связано с задачей,
    handler добавляет согласованные часы в actual_hours задачи.
    Данные: задача в реальной БД и WorklogApproved с task_id.
    """

    task = make_task(actual_hours=Decimal("1.5"))

    await task_repo.create(task)
    await session.commit()

    event = WorklogApproved(
        worklog_id=uuid4(),
        task_id=task.id,
        ticket_id=None,
        user_id=uuid4(),
        hours_spent=Decimal("2.25"),
        entry_date=date.today(),
        approved_by=uuid4(),
    )
    logger = FakeLogger()

    await on_worklog_approved(
        event=event,
        service=task_service,
        logger=logger,
    )

    updated_task = await task_repo.read(task.id)

    assert updated_task is not None
    assert updated_task.actual_hours == Decimal("3.75")
    assert logger.messages == []


@pytest.mark.asyncio
async def test_on_worklog_approved_without_task_id_does_not_update_task(session, task_repo, task_service):
    """
    Проверяем обработчик WorklogApproved: если в событии нет task_id,
    handler только пишет лог и не обновляет задачи.
    Данные: существующая задача и WorklogApproved с task_id=None.
    """

    task = make_task(actual_hours=Decimal("1.5"))

    await task_repo.create(task)
    await session.commit()

    event = WorklogApproved(
        worklog_id=uuid4(),
        task_id=None,
        ticket_id=None,
        user_id=uuid4(),
        hours_spent=Decimal("2.25"),
        entry_date=date.today(),
        approved_by=uuid4(),
    )
    logger = FakeLogger()

    await on_worklog_approved(
        event=event,
        service=task_service,
        logger=logger,
    )

    unchanged_task = await task_repo.read(task.id)

    assert unchanged_task is not None
    assert unchanged_task.actual_hours == Decimal("1.5")
    assert len(logger.messages) == 1