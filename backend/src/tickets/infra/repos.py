from typing import Any, Literal, override

from collections.abc import Callable
from uuid import UUID

from sqlalchemy import BinaryExpression, Select, and_, exists, func, or_, select
from sqlalchemy.orm import selectinload

from ...shared.infra.repos import SqlAlchemyRepository
from ...shared.schemas import Page, PageParams
from ..domain.entities import Comment, Membership, Project, Ticket
from ..domain.vo import CommentType, ProjectKey
from ..schemas import TicketFilter
from .mappers import CommentMapper, MembershipMapper, ProjectMapper, TicketMapper
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
        model = result.scalar_one_or_none()

        return None if model is None else self.model_mapper.to_entity(model)

    def _apply_filters(self, stmt: Select, filters: TicketFilter) -> Select:
        # Определение пары - фильтра и функции построения условия
        filter_conditions: list[tuple[Any, Callable[[Any], BinaryExpression]]] = [
            (filters.reporter_id, lambda value: self.model.reporter_id == value),
            (filters.creator_id, lambda value: self.model.created_by == value),
            (filters.project_id, lambda value: self.model.project_id == value),
            (filters.counterparty_id, lambda value: self.model.counterparty_id == value),
            (filters.status, lambda value: self.model.status == value),
            (filters.priority, lambda value: self.model.priority == value),
            (filters.assigned_to, lambda value: self.model.assigned_to == value),
            (filters.created_after, lambda value: self.model.created_at >= value),
            (filters.created_before, lambda value: self.model.created_at <= value),
            (
                filters.tags,
                lambda tags: or_(*[self.model.tags.contains([{"name": tag}]) for tag in tags]),
            ),
            (
                filters.search,
                lambda search: self.model.search_vector.op("@@")(
                    func.plainto_tsquery("russian", search)
                ),
            ),
        ]

        for value, condition_func in filter_conditions:
            if value is not None:
                stmt = stmt.where(condition_func(value))
        return stmt

    async def _paginate(self, stmt: Select, params: PageParams) -> Page[Ticket]:
        # 1. Получение общего количества
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_items = await self.session.scalar(count_stmt)
        if total_items == 0:
            return Page.create([], total_items, params.page, params.size)

        # 2. Получение страницы
        stmt = stmt.order_by(self.model.created_at.desc()).offset(params.offset).limit(params.size)
        results = await self.session.execute(stmt)
        models = results.scalars().all()

        # 3. На странице нет тикетов (пустая страница)
        if not models:
            return Page.create([], total_items, params.page, params.size)

        return Page.create(
            items=[self.model_mapper.to_preview(model) for model in models],
            total_items=total_items,
            page=params.page,
            size=params.size,
        )

    @override
    async def paginate(
        self, params: PageParams, filters: TicketFilter | None = None
    ) -> Page[Ticket]:
        # 1. Базовый запрос
        stmt = select(self.model)

        # 2. Применение фильтров
        if filters is not None:
            stmt = self._apply_filters(stmt, filters)

        return await self._paginate(stmt, params)

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

    async def get_by_reporter(self, reporter_id: UUID, params: PageParams) -> Page[Ticket]:
        # 1. Базовый запрос
        stmt = select(self.model).where(self.model.reporter_id == reporter_id)

        return await self._paginate(stmt, params)


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

    async def get_by_user_membership(
            self,
            user_id: UUID,
            pagination: PageParams,
            role: Literal["owner", "member", "all"] = "all",
    ) -> Page[Project]:
        # 1. Базовый запрос + проверка наличия членства в проекте
        stmt = select(self.model)
        membership_exists = exists().where(
            and_(
                MembershipOrm.project_id == self.model.id,
                MembershipOrm.user_id == user_id,
                MembershipOrm.removed_at.is_(None),
            )
        )

        # 2. Добавление фильтров в зависимости от выбранной роли
        if role == "owner":
            stmt = stmt.where(self.model.owner_id == user_id)
        elif role == "member":
            stmt = stmt.where(and_(self.model.owner_id != user_id, membership_exists))
        else:
            stmt = stmt.where(or_(self.model.owner_id == user_id, membership_exists))

        # 3. Подсчёт количества для пагинации
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_items = await self.session.scalar(count_stmt)
        if total_items == 0:
            return Page.create([], total_items, pagination.page, pagination.size)

        # 4. Получение проектов
        stmt = (
            stmt
            .order_by(self.model.created_at.desc())
            .offset(pagination.offset)
            .limit(pagination.size)
        )
        results = await self.session.execute(stmt)
        models = results.scalars().all()

        return Page.create(
            items=[self.model_mapper.to_entity(model) for model in models],
            total_items=total_items,
            page=pagination.page,
            size=pagination.size,
        )


class SqlCommentRepository(SqlAlchemyRepository[Comment, CommentOrm]):
    model = CommentOrm
    model_mapper = CommentMapper

    async def get_by_ticket(
            self,
            ticket_id: UUID,
            pagination: PageParams,
            *,
            user_id: UUID | None = None,
            include_notes: bool = False,
            include_internal: bool = False,
    ) -> Page[Comment]:
        # 1. Валидация входных параметров
        if user_id is None and include_notes:
            raise ValueError("User ID required for received NOTE comments")

        # 2. Базовый запрос для получения комментариев тикета
        stmt = select(self.model).where(self.model.ticket_id == ticket_id)

        # 3. Применение фильтров к запросу
        if include_notes:
            stmt = stmt.where(
                (self.model.comment_type == CommentType.NOTE) &
                (self.model.author_id == user_id)
            )
        if include_internal:
            stmt = stmt.where(self.model.comment_type == CommentType.INTERNAL)

        return await self._paginate(stmt, pagination)
