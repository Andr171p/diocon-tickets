from typing import override

from uuid import UUID

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.orm import selectinload

from src.shared.infra.repos import SqlAlchemyRepository
from src.shared.schemas import Page, Pagination

from ..domain.dtos import ActorsFilters
from ..domain.entities import Ticket
from ..domain.repos import TicketFilters
from .mappers import TicketMapper
from .models import TicketOrm


class SqlTicketRepository(SqlAlchemyRepository[Ticket, TicketOrm]):
    model = TicketOrm
    model_mapper = TicketMapper

    @override
    async def read(self, ticket_id: UUID) -> Ticket | None:
        stmt = (
            select(self.model)
            .where(self.model.id == ticket_id)
            .options(selectinload(self.model.attachments))
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        return None if model is None else self.model_mapper.to_entity(model)

    def _apply_actors_filters(
            self, stmt: Select[tuple[TicketOrm]], filters: ActorsFilters,
    ) -> Select[tuple[TicketOrm]]:
        if filters.assignee_id:
            stmt = stmt.where(self.model.assignee_id == filters.assignee_id)

        if filters.reporter_id:
            stmt = stmt.where(self.model.reporter_id == filters.reporter_id)

        if filters.creator_id:
            stmt = stmt.where(self.model.created_by == filters.creator_id)

        return stmt

    def _apply_ticket_filters(
            self, stmt: Select[tuple[TicketOrm]], filters: TicketFilters,
    ) -> Select[tuple[TicketOrm]]:
        if filters.statuses:
            stmt = stmt.where(self.model.status.in_(filters.statuses))

        if filters.priorities:
            stmt = stmt.where(self.model.priority.in_(filters.priorities))

        if filters.type:
            stmt = stmt.where(self.model.ticket_type == filters.type)

        if filters.tags:
            tag_conditions = [self.model.tags.contains([{"name": tag}]) for tag in filters.tags]
            stmt = stmt.where(or_(*tag_conditions))

        if filters.search_query:
            stmt = stmt.where(
                self.model.search_vector.op("@@")(
                    func.plainto_tsquery("russian", filters.search_query)
                )
            )

        if filters.actors:
            stmt = self._apply_actors_filters(stmt, filters.actors)

        if filters.time_range:
            stmt = self._apply_time_range_filters(stmt, filters.time_range)

        return stmt

    @override
    async def paginate(
            self, pagination: Pagination, filters: TicketFilters | None = None,
    ) -> Page[Ticket]:
        stmt = select(self.model)

        if filters is not None:
            stmt = self._apply_ticket_filters(stmt, filters)

        return await self._paginate(stmt, pagination, model_mapper=self.model_mapper.to_light)

    async def get_total(
            self, project_id: UUID | None = None, counterparty_id: UUID | None = None
    ) -> int:
        conditions = []

        if project_id is not None:
            conditions.append(self.model.project_id == project_id)
            if counterparty_id is not None:
                conditions.append(self.model.counterparty_id == counterparty_id)

        elif counterparty_id is not None and project_id is None:
            conditions.extend((
                self.model.counterparty_id == counterparty_id,
                self.model.project_id.is_(None)
            ))

        else:
            conditions.extend((
                self.model.project_id.is_(None), self.model.counterparty_id.is_(None),
            ))

        stmt = select(func.count()).select_from(self.model).where(and_(*conditions))
        return await self.session.scalar(stmt) or 0

    async def get_by_reporter(self, reporter_id: UUID, pagination: Pagination) -> Page[Ticket]:
        stmt = select(self.model).where(self.model.reporter_id == reporter_id)

        return await self._paginate(stmt, pagination)
