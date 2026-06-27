from decimal import Decimal
from uuid import UUID

from src.activity_logs.recorder import ActivityLogRecorder
from src.iam.domain.authz import Subject
from src.iam.domain.entities import User
from src.iam.domain.exceptions import PermissionDeniedError
from src.iam.domain.repos import UserRepository
from src.projects.domain.repos import ProjectRepository
from src.shared.domain.events import EventPublisher
from src.shared.domain.exceptions import InvalidStateError, NotFoundError
from src.shared.domain.repos import UnitOfWork, finalize, get_or_raise_404
from src.tickets.domain.entities import Ticket
from src.tickets.domain.repos import TicketRepository
from src.tickets.domain.vo import Tag

from ..domain.authz import TaskAuthZService
from ..domain.entities import Task
from ..domain.repos import TaskRepository
from ..domain.vo import TaskNumber, TaskStatus
from ..mappers import map_task_to_response
from ..schemas import ReviewDecision, TaskCreate, TaskResponse, TaskUpdate


class TaskService:
    def __init__(
            self,
            uow: UnitOfWork,
            task_repo: TaskRepository,
            ticket_repo: TicketRepository,
            user_repo: UserRepository,
            project_repo: ProjectRepository,
            task_authz_service: TaskAuthZService,
            activity_log_recorder: ActivityLogRecorder,
            event_publisher: EventPublisher,
    ) -> None:
        self.uow = uow
        self.task_repo = task_repo
        self.ticket_repo = ticket_repo
        self.user_repo = user_repo
        self.project_repo = project_repo
        self.task_authz_service = task_authz_service
        self.activity_log_recorder = activity_log_recorder
        self.event_publisher = event_publisher

    @staticmethod
    def _resolve_project_id(
            data: TaskCreate, ticket: Ticket | None = None
    ) -> UUID | None:
        """
        Определение правильного ID проекта для привязи к задаче.
        """

        project_id = data.project_id

        # Если указан тикет - проверка на его существование + подтягивание проекта
        if ticket is not None and ticket.project_id is not None:

            # Указанный проект и проект тикета должны совпадать
            if project_id is not None and project_id != ticket.project_id:
                raise InvalidStateError("Project mismatch with ticket")

            project_id = ticket.project_id

        return project_id

    async def create(self, data: TaskCreate, current_subject: Subject) -> TaskResponse:
        """
        Создание новой задачи.
        """

        permission = await self.task_authz_service.can_create_task(
            subject=current_subject, project_id=data.project_id
        )
        if not permission.allowed:
            raise PermissionDeniedError(permission.reason)

        ticket = None
        if data.ticket_id is not None:
            ticket = await self.ticket_repo.read(data.ticket_id)
            if ticket is None:
                raise NotFoundError(f"Ticket with ID {data.ticket_id} not found")

        project_id = self._resolve_project_id(data, ticket)

        project_key = None

        if project_id is not None:
            project = await self.project_repo.read(project_id)
            if project is None:
                raise NotFoundError(f"Project with ID {project_id} not found")

            project_key = project.key

        ticket_id = None if ticket is None else ticket.id
        sequence = await self.task_repo.get_next_sequence(
            ticket_id=ticket_id, project_id=project_id
        )

        ticket_number = None if ticket is None else ticket.number
        task_number = TaskNumber.create(
            ticket_number=ticket_number,
            project_key=project_key,
            sequence=sequence,
        )

        task = Task.create(
            number=task_number,
            title=data.title,
            description=data.description,
            priority=data.priority,
            due_date=data.due_date,
            estimated_hours=data.estimated_hours,
            project_id=project_id,
            ticket_id=data.ticket_id,
            created_by=current_subject.id,
            tags=[Tag(name=tag.name, color=tag.color) for tag in data.tags]
        )
        if data.mark_as_todo:
            task.change_status(new_status=TaskStatus.TODO, changed_by=current_subject.id)

        await self.task_repo.create(task)

        await finalize(
            self.uow, task,
            event_publisher=self.event_publisher,
            activity_recorder=self.activity_log_recorder
        )

        return map_task_to_response(task)

    async def change_status(
            self, task_id: UUID, new_status: TaskStatus, current_subject: Subject
    ) -> TaskResponse:
        """
        Изменение статуса задачи.
        """

        task = await get_or_raise_404(self.task_repo.read, task_id, Task)

        permission = await self.task_authz_service.can_change_status(
            subject=current_subject, task=task, new_status=new_status
        )
        if not permission.allowed:
            raise PermissionDeniedError(permission.reason)

        task.change_status(new_status=new_status, changed_by=current_subject.id)
        await self.task_repo.update(task)

        await finalize(
            self.uow, task,
            event_publisher=self.event_publisher,
            activity_recorder=self.activity_log_recorder
        )

        return map_task_to_response(task)

    async def edit(
            self, task_id: UUID, data: TaskUpdate, current_subject: Subject
    ) -> TaskResponse:
        """
        Редактировать содержание задачи.
        """

        task = await get_or_raise_404(self.task_repo.read, task_id, Task)

        permission = await self.task_authz_service.can_edit_task(
            subject=current_subject, task=task
        )
        if not permission.allowed:
            raise PermissionDeniedError(permission.reason)

        task.edit(
            title=data.title,
            description=data.description,
            priority=data.priority,
            story_points=data.story_points,
            estimated_hours=data.estimated_hours,
            due_date=data.due_date,
        )
        await self.task_repo.update(task)

        await finalize(
            self.uow, task,
            event_publisher=self.event_publisher,
            activity_recorder=self.activity_log_recorder
        )

        return map_task_to_response(task)

    async def assign_to(
            self, task_id: UUID, assignee_id: UUID, current_subject: Subject
    ) -> TaskResponse:
        """
        Назначить исполнителя на задачу.
        """

        task = await get_or_raise_404(self.task_repo.read, task_id, Task)
        assignee = await get_or_raise_404(self.user_repo.read, assignee_id, User)

        permission = await self.task_authz_service.can_assign_task(
            subject=current_subject, task=task, assignee=assignee
        )
        if not permission.allowed:
            raise PermissionDeniedError(permission.reason)

        task.assign_to(assignee_id=assignee_id, assigned_by=current_subject.id)
        await self.task_repo.update(task)

        await finalize(
            self.uow, task,
            event_publisher=self.event_publisher,
            activity_recorder=self.activity_log_recorder
        )

        return map_task_to_response(task)

    async def request_review(
            self, task_id: UUID, reviewer_id: UUID, current_subject: Subject
    ) -> TaskResponse:
        """
        Запросить ревью на задачу у пользователя.
        """

        task = await get_or_raise_404(self.task_repo.read, task_id, Task)
        reviewer = await get_or_raise_404(self.user_repo.read, reviewer_id, User)

        permission = await self.task_authz_service.can_review_task(
            subject=current_subject, task=task, reviewer=reviewer
        )
        if not permission.allowed:
            raise PermissionDeniedError(permission.reason)

        task.request_review(reviewer_id=reviewer_id, requested_by=current_subject.id)
        await self.task_repo.update(task)

        await finalize(
            self.uow, task,
            event_publisher=self.event_publisher,
            activity_recorder=self.activity_log_recorder
        )

        return map_task_to_response(task)

    async def review(
            self, task_id: UUID, decision: ReviewDecision, current_subject: Subject
    ) -> TaskResponse:
        """
        Провести ревью задачи.
        """

        task = await get_or_raise_404(self.task_repo.read, task_id, Task)

        permission = await self.task_authz_service.can_review_task(
            subject=current_subject, task=task
        )
        if not permission.allowed:
            raise PermissionDeniedError(permission.reason)

        task.complete_review(decision, reviewed_by=current_subject.id)
        await self.task_repo.update(task)

        await finalize(
            self.uow, task,
            event_publisher=self.event_publisher,
            activity_recorder=self.activity_log_recorder
        )

        return map_task_to_response(task)

    async def archive(self, task_id: UUID, current_subject: Subject) -> TaskResponse:
        """
        Перенос задачи в архив.
        """

        task = await get_or_raise_404(self.task_repo.read, task_id, Task)

        permission = await self.task_authz_service.can_archive_task(
            subject=current_subject, task=task
        )
        if not permission.allowed:
            raise PermissionDeniedError(permission.reason)

        task.archive(archived_by=current_subject.id)
        await self.task_repo.update(task)

        await finalize(
            self.uow, task,
            event_publisher=self.event_publisher,
            activity_recorder=self.activity_log_recorder
        )

        return map_task_to_response(task)

    async def add_actual_hours(self, task_id: UUID, hours: Decimal) -> None:
        """
        Добавить факт потраченного времени на задачу.
        """

        task = await get_or_raise_404(self.task_repo.read, task_id, Task)

        task.add_actual_hours(hours)
        await self.task_repo.update(task)

        await finalize(
            self.uow, task,
            event_publisher=self.event_publisher,
            activity_recorder=self.activity_log_recorder
        )
