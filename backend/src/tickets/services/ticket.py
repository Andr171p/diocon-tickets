from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ...crm.domain.repo import CounterpartyRepository
from ...iam.domain.exceptions import PermissionDeniedError
from ...iam.domain.vo import UserRole
from ...shared.domain.events import EventPublisher
from ...shared.domain.exceptions import NotFoundError
from ..domain.entities import Ticket
from ..domain.repos import ProjectRepository, TicketRepository
from ..domain.services import ProjectAccessService
from ..domain.vo import ProjectKey, Tag, TicketNumber, TicketStatus
from ..mappers import map_ticket_to_response
from ..schemas import TicketCreate, TicketResponse

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
            project_repo: ProjectRepository,
            counterparty_repo: CounterpartyRepository,
            event_publisher: EventPublisher,
    ) -> None:
        self.session = session
        self.ticket_repo = ticket_repo
        self.project_repo = project_repo
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

        # 3. Атомарная операция для создания тикета
        async with self.session.begin():

            # 4. Генерация уникального номера
            total_tickets = await self.ticket_repo.get_total(
                project_id=data.project_id, counterparty_id=data.counterparty_id
            )
            ticket_number = TicketNumber.create(
                total_tickets,
                project_key=context.project_key,
                counterparty_name=context.counterparty_name,
            )

            # 5. Создание и сохранение доменной сущности
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

        # 6. Публикация доменных событий
        for event in ticket.collect_events():
            await self.event_publisher.publish(event)

        return map_ticket_to_response(ticket)

    async def assign_to(self): ...

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

    async def close(self): ...
