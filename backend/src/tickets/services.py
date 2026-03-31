from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ..iam.domain.vo import UserRole
from ..shared.domain.events import EventPublisher
from .domain.entities import Ticket
from .domain.repo import TicketRepository
from .schemas import TicketCreate


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
    ):
        ticket = Ticket.create(
            created_by=created_by,
            created_by_role=created_by_role,
            title=data.title,
            description=data.description,
            priority=data.priority,
            counterparty_id=data.counterparty_id,
        )
        await self.repository.create(ticket)

        for event in ticket.collect_events():
            await self.event_publisher.publish(event)

        await self.session.commit()

        return ...

    async def assign_to(self): ...

    async def change_status(self): ...

    async def close(self): ...
