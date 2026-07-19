from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from functools import partial
from uuid import UUID

from src.activity_logs.recorder import ActivityLogRecorder
from src.crm.domain.entities import Counterparty
from src.crm.domain.repo import CounterpartyRepository
from src.iam.domain.authz import PermissionResult, Subject
from src.iam.domain.entities import User
from src.iam.domain.exceptions import PermissionDeniedError
from src.iam.domain.repos import UserRepository
from src.projects.domain.entities import Project
from src.projects.domain.repos import ProjectRepository
from src.shared.domain.events import EventPublisher
from src.shared.domain.repos import UnitOfWork, finalize, get_or_raise_404
from src.shared.domain.vo import Tag

from ..domain.authz import TicketAuthZService
from ..domain.dtos import TicketDraft
from ..domain.entities import Ticket
from ..domain.repos import TicketRepository
from ..domain.services import create_ticket
from ..mappers import map_ticket_to_response
from ..schemas import TicketCreate, TicketUpdate, TicketResponse


@dataclass(frozen=True, slots=True)
class _TicketCreationContext:
    project: Project | None = None
    counterparty: Counterparty | None = None

    @property
    def project_id(self) -> UUID | None:
        return self.project.id if self.project else None

    @property
    def counterparty_id(self) -> UUID | None:
        return self.counterparty.id if self.counterparty else None


class TicketService:
    def __init__(
            self,
            uow: UnitOfWork,
            ticket_repo: TicketRepository,
            project_repo: ProjectRepository,
            user_repo: UserRepository,
            counterparty_repo: CounterpartyRepository,
            authz_service: TicketAuthZService,
            activity_log_recorder: ActivityLogRecorder,
            event_publisher: EventPublisher,
    ) -> None:
        self.uow = uow
        self.ticket_repo = ticket_repo
        self.project_repo = project_repo
        self.user_repo = user_repo
        self.counterparty_repo = counterparty_repo
        self.authz_service = authz_service
        self.activity_log_recorder = activity_log_recorder
        self.event_publisher = event_publisher

    async def _resolve_creation_context(self, data: TicketCreate) -> _TicketCreationContext:
        """
        Определяет контекст создания заявки.

        Валидирует, что заявка создаётся только в одном контексте:
        - внутри проекта;
        - для контрагента;
        - либо как внутренняя заявка.

        Если указан проект, связанный с ним контрагент автоматически
        разрешается и включается в контекст.

        Возвращаемый контекст содержит все доменные объекты, необходимые
        для проверки прав, генерации номера заявки и создания агрегата.
        """

        if data.project_id is not None and data.counterparty_id is not None:
            raise ValueError("Only one of the project or counterparty must be specified.")

        if data.project_id:
            project = await get_or_raise_404(self.project_repo.read, data.project_id, Project)

            counterparty = None
            if project.counterparty_id:
                counterparty = await get_or_raise_404(
                    self.counterparty_repo.read, project.counterparty_id, Counterparty,
                )

            return _TicketCreationContext(project=project, counterparty=counterparty)

        if data.counterparty_id:
            counterparty = await get_or_raise_404(
                self.counterparty_repo.read, data.counterparty_id, Counterparty,
            )
            return _TicketCreationContext(counterparty=counterparty)

        return _TicketCreationContext()

    async def create(self, data: TicketCreate, current_subject: Subject) -> TicketResponse:

        context = await self._resolve_creation_context(data)

        permission = await self.authz_service.can_create_ticket(
            subject=current_subject,
            counterparty_id=context.counterparty_id,
            project_id=context.project_id,
        )
        if not permission.allowed:
            raise PermissionDeniedError(permission.reason)

        sequence = await self.ticket_repo.get_next_sequence(
            project_id=context.project_id,
            counterparty_id=context.counterparty_id,
        )
        tags = [Tag(name=tag.name, color=tag.color) for tag in data.tags]
        draft = TicketDraft(
            title=data.title,
            description=data.description,
            reporter_id=data.reporter_id,
            created_by=current_subject.id,
            type=data.type,
            priority=data.priority,
            tags=tags,
            project=context.project,
            counterparty=context.counterparty,
            product_id=data.product_id,
        )
        ticket = create_ticket(draft, sequence=sequence)

        await self.ticket_repo.create(ticket)
        await finalize(
            self.uow, ticket,
            activity_recorder=self.activity_log_recorder,
            event_publisher=self.event_publisher,
        )

        return map_ticket_to_response(ticket)

    async def _execute(
            self,
            ticket_id: UUID,
            current_subject: Subject,
            authz: Callable[[Subject, Ticket], Awaitable[PermissionResult]],
            action: Callable[[Ticket], None],
    ) -> TicketResponse:
        ticket = await get_or_raise_404(self.ticket_repo.read, ticket_id, Ticket)

        permission = await authz(current_subject, ticket)
        if not permission.allowed:
            raise PermissionDeniedError(permission.reason)

        action(ticket)
        await self.ticket_repo.update(ticket)

        await finalize(
            self.uow, ticket,
            activity_recorder=self.activity_log_recorder,
            event_publisher=self.event_publisher,
        )

        return map_ticket_to_response(ticket)

    async def edit(
            self, ticket_id: UUID, data: TicketUpdate, current_subject: Subject,
    ) -> TicketResponse:
        """Отредактировать заявку."""

        tags = (
            None if data.tags is None else
            [Tag(name=tag.name, color=tag.color) for tag in data.tags]
        )

        return await self._execute(
            ticket_id=ticket_id,
            current_subject=current_subject,
            authz=self.authz_service.can_edit_ticket,
            action=lambda t: t.edit(
                edited_by=current_subject.id,
                title=data.title,
                description=data.description,
                priority=data.priority,
                tags=tags,
            )
        )

    async def archive(self, ticket_id: UUID, current_subject: Subject) -> TicketResponse:
        """Перенести заявку в архив."""

        return await self._execute(
            ticket_id=ticket_id,
            current_subject=current_subject,
            authz=self.authz_service.can_archive_ticket,
            action=lambda t: t.archive(current_subject.id),
        )

    async def assign(
            self, ticket_id: UUID, assignee_id: UUID, current_subject: Subject,
    ) -> TicketResponse:
        """Назначить исполнителя на заявку."""

        assignee = await get_or_raise_404(self.user_repo.read, assignee_id, User)

        authz = partial(self.authz_service.can_assign_ticket, assignee=assignee)

        return await self._execute(
            ticket_id=ticket_id,
            current_subject=current_subject,
            authz=authz,
            action=lambda t: t.assign(assignee_id=assignee.id, actor_id=current_subject.id),
        )

    async def start_progress(self, ticket_id: UUID, current_subject: Subject) -> TicketResponse:
        """Взять тикет в работу."""

        return await self._execute(
            ticket_id=ticket_id,
            current_subject=current_subject,
            authz=self.authz_service.can_manage_ticket,
            action=lambda t: t.start_progress(current_subject.id),
        )

    async def resolve(self, ticket_id: UUID, current_subject: Subject) -> TicketResponse:
        """Решить тикет."""

        return await self._execute(
            ticket_id=ticket_id,
            current_subject=current_subject,
            authz=self.authz_service.can_manage_ticket,
            action=lambda t: t.resolve(current_subject.id),
        )

    async def close(self, ticket_id: UUID, current_subject: Subject) -> TicketResponse:
        """Закрыть тикет."""

        return await self._execute(
            ticket_id=ticket_id,
            current_subject=current_subject,
            authz=self.authz_service.can_close_ticket,
            action=lambda t: t.close(current_subject.id),
        )

    async def cancel(self, ticket_id: UUID, current_subject: Subject) -> TicketResponse:
        """Отменить тикет."""

        return await self._execute(
            ticket_id=ticket_id,
            current_subject=current_subject,
            authz=self.authz_service.can_cancel_ticket,
            action=lambda t: t.cancel(current_subject.id),
        )

    async def reject(self, ticket_id: UUID, current_subject: Subject) -> TicketResponse:
        """Отклонить тикет."""

        return await self._execute(
            ticket_id=ticket_id,
            current_subject=current_subject,
            authz=self.authz_service.can_reject_ticket,
            action=lambda t: t.reject(current_subject.id),
        )
