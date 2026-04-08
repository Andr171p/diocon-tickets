from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..iam.domain.vo import UserRole
from ..shared.domain.events import EventPublisher
from ..shared.domain.exceptions import AlreadyExistsError
from .domain.entities import Project, Ticket
from .domain.repos import ProjectRepository, TicketRepository
from .domain.vo import ProjectKey, Tag
from .mappers import map_project_to_response, map_ticket_to_response
from .schemas import KeyCheckResponse, ProjectCreate, ProjectResponse, TicketCreate, TicketResponse


class TicketService:
    def __init__(
            self,
            session: AsyncSession,
            repository: TicketRepository,
            event_publisher: EventPublisher,
    ) -> None:
        self.session = session
        self.repository = repository
        self.event_publisher = event_publisher

    async def create(
            self, data: TicketCreate, created_by: UUID, created_by_role: UserRole
    ) -> TicketResponse:
        """Создание тикета"""

        # 1. Создание и сохранения доменной модели
        ticket = Ticket.create(
            created_by=created_by,
            created_by_role=created_by_role,
            reporter_id=data.reporter_id,
            title=data.title,
            description=data.description,
            priority=data.priority,
            counterparty_id=data.counterparty_id,
            counterparty_name=data.counterparty_name,
            tags=[Tag(name=tag.name, color=tag.color) for tag in data.tags],
        )
        await self.repository.create(ticket)
        await self.session.commit()

        # 2. Публикация событий
        for event in ticket.collect_events():
            await self.event_publisher.publish(event)

        return map_ticket_to_response(ticket)

    async def assign_to(self): ...

    async def change_status(self): ...

    async def close(self): ...


class ProjectService:
    def __init__(self, session: AsyncSession, repository: ProjectRepository) -> None:
        self.session = session
        self.repository = repository

    async def check_key(self, project_key: str) -> KeyCheckResponse:

        # 1. Проверка текущего проекта
        project_key = ProjectKey(project_key)
        project = await self.repository.get_by_key(project_key)
        if project is None:
            return KeyCheckResponse(available=True)

        # 2. Генерация альтернатив
        suggestions = await self._generate_key_suggestions(project_key.value)
        return KeyCheckResponse(available=False, suggestions=suggestions)

    async def _generate_key_suggestions(
            self, original_key: str, max_attempts: int = 5
    ) -> list[str]:
        ...

    async def create(
            self, data: ProjectCreate, created_by: UUID, max_attempts: int = 5
    ) -> ProjectResponse:
        """
        Создание проекта с уникальным ключом
        """

        key_candidate = data.key
        for attempt in range(max_attempts):
            try:
                project = Project.create(
                    name=data.name,
                    key=key_candidate,
                    description=data.description,
                    counterparty_id=data.counterparty_id,
                    owner_id=data.owner_id,
                    created_by=created_by,
                )
                await self.repository.create(project)
                await self.session.flush()
            except IntegrityError:
                await self.session.rollback()
                key_candidate = f"{key_candidate}{attempt}"
            else:
                await self.session.commit()
                return map_project_to_response(project)
        raise AlreadyExistsError(
            f"Project with key - {key_candidate} already exists. "
            f"{max_attempts} attempts were not enough to resolve the uniqueness of the key. "
            f"Try again with a different key.",
            details={"last_suggested_key": key_candidate}
        )
