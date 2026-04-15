from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ...crm.domain.repo import CounterpartyRepository
from ...iam.domain.exceptions import PermissionDeniedError
from ...iam.domain.repos import UserRepository
from ...iam.domain.vo import UserRole
from ...iam.schemas import CurrentUser
from ...shared.domain.events import EventPublisher
from ...shared.domain.exceptions import NotFoundError
from ...shared.schemas import Page, PageParams
from ..domain.entities import Comment, Ticket
from ..domain.repos import CommentRepository, ProjectRepository, TicketRepository
from ..domain.services import ProjectAccessService, can_access_ticket
from ..domain.vo import ProjectKey, Tag, TicketNumber, TicketStatus
from ..mappers import map_comment_to_response, map_ticket_to_response
from ..schemas import CommentCreate, CommentEdit, CommentResponse, TicketCreate, TicketResponse

# Длина короткого ключа проекта
SHORT_PROJECT_KEY_LENGTH = 3


@dataclass
class TicketCreationContext:
    """Контекст для создания тикета"""

    project_id: UUID | None = None
    project_key: ProjectKey | None = None
    counterparty_id: UUID | None = None
    counterparty_name: str | None = None


class TicketService:
    def __init__(
            self,
            session: AsyncSession,
            ticket_repo: TicketRepository,
            comment_repo: CommentRepository,
            project_repo: ProjectRepository,
            user_repo: UserRepository,
            counterparty_repo: CounterpartyRepository,
            event_publisher: EventPublisher,
    ) -> None:
        self.session = session
        self.ticket_repo = ticket_repo
        self.comment_repo = comment_repo
        self.project_repo = project_repo
        self.user_repo = user_repo
        self.counterparty_repo = counterparty_repo
        self.project_access_service = ProjectAccessService(project_repo)
        self.event_publisher = event_publisher

    async def _determine_creation_context(self, data: TicketCreate) -> TicketCreationContext:
        """
        Определение контекста создания тикета и валидация входных данных

        - Если указан project_id, то counterparty_id подтягивается из проекта.
        - Если указан counterparty_id, то используется напрямую.
        - Если не указан ни project_id, ни counterparty_id, то контекст зануляется.
        """

        if data.project_id is not None and data.counterparty_id is not None:
            raise ValueError("Only one of the project or counterparty must be specified")

        # 1. Тикет создаётся в рамках проекта
        if data.project_id is not None:
            project = await self.project_repo.read(data.project_id)
            if project is None:
                raise NotFoundError(f"Project with ID {data.project_id} not found")

            return TicketCreationContext(
                project_id=data.project_id,
                project_key=project.key,
                counterparty_id=project.counterparty_id,
                counterparty_name=None,
            )

        # 2. Тикет привязан к контрагенту
        if data.counterparty_id is not None:
            counterparty = await self.counterparty_repo.read(data.counterparty_id)
            if counterparty is None:
                raise NotFoundError(f"Counterparty with ID {data.counterparty_id} not found")

            return TicketCreationContext(
                project_id=None,
                project_key=None,
                counterparty_id=counterparty.id,
                counterparty_name=counterparty.name,
            )

        return TicketCreationContext(
            project_id=None,
            project_key=None,
            counterparty_id=None,
            counterparty_name=None,
        )

    async def create(
            self, data: TicketCreate, created_by: UUID, created_by_role: UserRole
    ) -> TicketResponse:
        """Создание тикета"""

        # 1. Определение контекста создания тикета
        context = await self._determine_creation_context(data)

        # 2. Проверка прав доступа
        if context.project_id is not None:
            can_create = await self.project_access_service.can_create_ticket(
                project_id=context.project_id, user_id=created_by, user_role=created_by_role
            )
            if not can_create:
                raise PermissionDeniedError(
                    "You do not have permissions to create tickets in this project"
                )

        # 3. Генерация уникального номера
        total_tickets = await self.ticket_repo.get_total(
            project_id=data.project_id, counterparty_id=data.counterparty_id
        )
        ticket_number = TicketNumber.create(
            total_tickets,
            project_key=context.project_key,
            counterparty_name=context.counterparty_name,
        )

        # 4. Создание и сохранение доменной сущности
        ticket = Ticket.create(
            ticket_number=ticket_number,
            created_by=created_by,
            created_by_role=created_by_role,
            reporter_id=data.reporter_id,
            title=data.title,
            description=data.description,
            priority=data.priority,
            project_id=context.project_id,
            counterparty_id=context.counterparty_id,
            tags=[Tag(name=tag.name, color=tag.color) for tag in data.tags],
        )
        await self.ticket_repo.create(ticket)
        await self.session.commit()

        # 5. Публикация доменных событий
        for event in ticket.collect_events():
            await self.event_publisher.publish(event)

        return map_ticket_to_response(ticket)

    async def assign_to(
            self, ticket_id: UUID, assignee_id: UUID, assigned_by: UUID, assigned_by_role: UserRole
    ) -> TicketResponse:
        """Назначение тикета на исполнителя"""

        # 1. Получение тикета
        ticket = await self.ticket_repo.read(ticket_id)
        if ticket is None:
            raise NotFoundError(f"Ticket with ID {ticket_id} not found")

        # 2. Проверка прав в проекте, если тикет принадлежит проекту
        if ticket.project_id is not None:
            can_assign = await self.project_access_service.can_assign_ticket(
                project_id=ticket.project_id,
                user_id=assigned_by,
                user_role=assigned_by_role
            )
            if not can_assign:
                raise PermissionDeniedError("No permission to assign tickets in this project")

        # 3. Загрузка пользователя на которого назначается тикет
        assignee = await self.user_repo.read(assignee_id)
        if assignee is None:
            raise NotFoundError(f"User with ID {assignee_id} not found")

        # 4. Назначение исполнителя и обновление сущности
        ticket.assign_to(
            assignee_id=assignee_id,
            assignee_role=assignee.role,
            assigned_by=assigned_by,
            assigned_by_role=assigned_by_role,
        )
        await self.ticket_repo.upsert(ticket)
        await self.session.commit()

        # 5. Публикация доменных событий
        for event in ticket.collect_events():
            await self.event_publisher.publish(event)

        return map_ticket_to_response(ticket)

    async def change_status(
            self,
            ticket_id: UUID,
            new_status: TicketStatus,
            changed_by: UUID,
            changed_by_role: UserRole
    ) -> TicketResponse:
        """Изменение статуса тикета"""

        # 1. Получение тикета и проверка на существование
        ticket = await self.ticket_repo.read(ticket_id)
        if ticket is None:
            raise NotFoundError(f"Ticket with ID {ticket_id} not found")

        # 2. Если тикет принадлежит проекту, то проверка внутри-проектных прав
        if ticket.project_id is not None:
            can_change = await self.project_access_service.can_change_status(
                project_id=ticket.project_id,
                user_id=changed_by,
                user_role=changed_by_role,
            )
            if not can_change:
                raise PermissionDeniedError("No permission to change status in this project")

        # 3. Изменение статуса и обновление доменной сущности
        ticket.change_status(new_status, changed_by, changed_by_role)
        await self.ticket_repo.upsert(ticket)
        await self.session.commit()

        # 4. Публикация доменных событий
        for event in ticket.collect_events():
            await self.event_publisher.publish(event)

        return map_ticket_to_response(ticket)

    async def add_comment(
            self, ticket_id: UUID, data: CommentCreate, current_user: CurrentUser
    ) -> CommentResponse:
        """Добавление комментария к тикету"""

        # 1. Получение тикета
        ticket = await self.ticket_repo.read(ticket_id)
        if ticket is None:
            raise NotFoundError(f"Ticket with ID {ticket_id} not found")

        # 2. Клиент может комментировать только свои тикеты
        if current_user.role == UserRole.CUSTOMER and current_user.user_id != ticket.reporter_id:
            raise PermissionDeniedError(
                "You can only comment on tickets where you are the reporter"
            )

        # 3. Администратор клиента может комментировать все тикеты своего контрагента
        if current_user.role == UserRole.CUSTOMER_ADMIN \
                and current_user.counterparty_id != ticket.counterparty_id:
            raise PermissionDeniedError("You can only comment on tickets of your counterparty")

        # 4. Создание комментария + запись в историю тикета
        comment = Comment.create(
            ticket_id=ticket_id,
            author_id=current_user.user_id,
            author_role=current_user.role,
            text=data.text,
            comment_type=data.type,
        )
        ticket.write_history(
            actor_id=current_user.user_id,
            action="comment_added",
            description=f"Добавлен новый комментарий: '{comment.text[:100]}'",
        )
        await self.comment_repo.create(comment)
        await self.ticket_repo.upsert(ticket)
        await self.session.commit()

        # 5. Публикация доменных событий
        for event in comment.collect_events():
            await self.event_publisher.publish(event)

        return map_comment_to_response(comment)

    async def edit_comment(
            self, ticket_id: UUID, comment_id: UUID, data: CommentEdit, edited_by: UUID
    ) -> CommentResponse:
        """Редактирование комментария"""

        # 1. Получение тикета и комментария
        ticket = await self.ticket_repo.read(ticket_id)
        if ticket is None:
            raise NotFoundError(f"Ticket with ID {ticket_id} not found")

        comment = await self.comment_repo.read(comment_id)
        if comment is None:
            raise NotFoundError(f"Comment with ID {comment_id} not found")

        # 2. Редактирование комментария и обновление сущности
        comment.edit(new_text=data.text, edited_by=edited_by)
        if comment.text != data.text.strip():  # Если текст изменён, то записывается в историю
            ticket.write_history(
                actor_id=edited_by,
                action="comment_edited",
                description=f"Комментарий отредактирован: '{data.text[:100]}'",
                old_value=comment.text[:100],
                new_value=data.text[:100],
            )
        await self.comment_repo.upsert(comment)
        await self.ticket_repo.upsert(ticket)
        await self.session.commit()

        # 3. Публикация доменных событий
        for event in comment.collect_events():
            await self.event_publisher.publish(event)

        return map_comment_to_response(comment)

    async def delete_comment(self, ticket_id: UUID, comment_id: UUID, deleted_by: UUID) -> None:
        """Удаление комментария"""

        # 1. Получение тикета и комментария
        ticket = await self.ticket_repo.read(ticket_id)
        if ticket is None:
            raise NotFoundError(f"Ticket with ID {ticket_id} not found")

        comment = await self.comment_repo.read(comment_id)
        if comment is None:
            raise NotFoundError(f"Comment with ID {comment_id} not found")

        # 2. Удалять комментарий может только автор
        if deleted_by != comment.author_id:
            raise PermissionDeniedError("Only author can delete comments")

        # 3. Удаление и запись в историю
        await self.comment_repo.delete(comment_id)
        ticket.write_history(
            actor_id=deleted_by,
            action="comment_deleted",
            description=f"Комментарий удалён: '{comment.text[:100]}'",
            old_value=comment.text[:100],
            new_value=None,
        )
        await self.ticket_repo.upsert(ticket)
        await self.session.commit()

    async def get_comments(
            self,
            ticket_id: UUID,
            pagination: PageParams,
            current_user: CurrentUser,
            include_internal: bool = False,
    ) -> Page[CommentResponse]:
        """Получение комментариев к тикету с учётом прав"""

        # 1. Получение тикета
        ticket = await self.ticket_repo.read(ticket_id)
        if ticket is None:
            raise NotFoundError(f"Ticket with ID {ticket_id} not found")

        # 2. Имеется ли у пользователя доступ к тикету
        if not can_access_ticket(
            ticket,
            user_id=current_user.user_id,
            user_role=current_user.role,
            user_counterparty_id=current_user.counterparty_id,
        ):
            raise PermissionDeniedError("You cannot view this ticket")

        # 3. Проверка прав на просмотр внутренних комментариев
        if include_internal and not current_user.role.is_support():
            raise PermissionDeniedError("Only support team can view internal comments")

        # 4. Получение страницы с комментариями
        page = await self.comment_repo.get_by_ticket(
            ticket_id=ticket_id,
            pagination=pagination,
            user_id=current_user.user_id,
            include_notes=True,
            include_internal=include_internal,
        )

        return page.to_response(map_comment_to_response)
