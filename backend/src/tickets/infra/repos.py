from typing import override

from uuid import UUID

from sqlalchemy import Select, and_, func, select
from sqlalchemy.orm import attributes, selectinload

from ...shared.infra.repos import SqlAlchemyRepository
from ...shared.schemas import Page, PageParams
from ..domain.entities import Membership, Project, Ticket
from ..domain.vo import ProjectKey, TicketPriority, TicketStatus
from .mappers import MembershipMapper, ProjectMapper, TicketMapper
from .models import CommentOrm, MembershipOrm, ProjectOrm, TicketOrm


class SqlTicketRepository(SqlAlchemyRepository[Ticket, TicketOrm]):
    model = TicketOrm
    model_mapper = TicketMapper

    @override
    async def read(self, ticket_id: UUID, comments_limit: int = 10) -> Ticket | None:
        # 1. Получение тикета с вложениями и историей изменений
        stmt = (
            select(self.model)
            .where(self.model.id == ticket_id)
            .options(
                selectinload(self.model.history),
                selectinload(self.model.attachments),
            )
        )
        result = await self.session.execute(stmt)
        ticket = result.scalar_one_or_none()
        if ticket is None:
            return None

        # 2. Получение комментариев с заданным лимитом
        comments_stmt = (
            select(CommentOrm)
            .where(CommentOrm.ticket_id == ticket_id)
            .order_by(CommentOrm.created_at.desc())
            .limit(comments_limit)
            .options(selectinload(CommentOrm.attachments))
        )
        results = await self.session.execute(comments_stmt)
        comments = results.scalars().all()

        # 3. Установка загруженных комментариев в объект
        attributes.set_committed_value(ticket, "comments", comments)

        return self.model_mapper.to_entity(ticket)

    def _apply_filters(
            self,
            query: Select,
            creator_id: UUID | None = None,
            counterparty_id: UUID | None = None,
            status: TicketStatus | None = None,
            priority: TicketPriority | None = None
    ) -> Select:
        if creator_id is not None:
            query = query.where(self.model.created_by == creator_id)
        if counterparty_id is not None:
            query = query.where(self.model.counterparty_id == counterparty_id)
        if status is not None:
            query = query.where(self.model.status == status)
        if priority is not None:
            query = query.where(self.model.priority == priority)
        return query

    @override
    async def paginate(
        self,
        params: PageParams,
        creator_id: UUID | None = None,
        counterparty_id: UUID | None = None,
        status: TicketStatus | None = None,
        priority: TicketPriority | None = None,
    ) -> Page[Ticket]:
        # 1. Подсчёт общего количества тикетов для пагинации, учитывая фильтрацию
        count_stmt = self._apply_filters(
            select(func.count()), creator_id, counterparty_id, status, priority
        )

        total_items = await self.session.scalar(count_stmt)
        if total_items == 0:
            return Page.create([], total_items, params.page, params.size)

        # 2. Запрос для получения тикетов, с учётом фильтрации
        stmt = self._apply_filters(
            select(self.model), creator_id, counterparty_id, status, priority
        )
        stmt = stmt.order_by(self.model.created_at.desc()).offset(params.offset).limit(params.size)

        results = await self.session.execute(stmt)
        models = results.scalars().all()

        # 3. Для станицы не нашлось тикетов
        if not models:
            return Page.create([], total_items, params.page, params.size)

        # 4. Формирование страницы
        return Page.create(
            items=[self.model_mapper.to_preview_entity(model) for model in models],
            total_items=total_items,
            page=params.page,
            size=params.size,
        )

    async def get_total(
            self, project_id: UUID | None = None, counterparty_id: UUID | None = None
    ) -> int:
        # 1. Генерация комбинаций фильтров
        filters = [
            self.model.project_id.is_(None) if project_id is None
            else self.model.project_id == project_id,
            self.model.counterparty_id.is_(None) if counterparty_id is None
            else self.model.counterparty_id == counterparty_id
        ]

        # 2. Запрос с применением фильтров
        stmt = select(func.count()).select_from(self.model).where(and_(*filters))
        return await self.session.scalar(stmt)


class SqlProjectRepository(SqlAlchemyRepository[Project, ProjectOrm]):
    model = ProjectOrm
    model_mapper = ProjectMapper

    async def get_by_key(self, key: ProjectKey) -> Project | None:
        stmt = select(self.model).where(self.model.key == key.value)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return None if model is None else self.model_mapper.to_entity(model)

    async def get_existing_keys(self, keys: list[str]) -> set[str]:
        if not keys:
            return set()

        stmt = select(self.model.key).where(self.model.key.in_(keys))
        result = await self.session.execute(stmt)

        return {row[0] for row in result.all()}

    async def get_membership(self, project_id: UUID, user_id: UUID) -> Membership | None:
        stmt = (
            select(MembershipOrm)
            .where(
                (MembershipOrm.project_id == project_id) &
                (MembershipOrm.user_id == user_id)
            )
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return None if model is None else MembershipMapper.to_entity(model)
