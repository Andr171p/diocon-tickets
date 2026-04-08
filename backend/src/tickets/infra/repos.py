from typing import override

from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.orm import attributes, selectinload

from ...media.infra.repo import AttachmentMapper
from ...shared.infra.repos import ModelMapper, SqlAlchemyRepository
from ...shared.schemas import Page, PageParams
from ..domain.entities import Comment, Participant, Project, Ticket, TicketHistoryEntry
from ..domain.vo import ProjectKey, Tag, TicketNumber, TicketPriority, TicketStatus
from .models import CommentOrm, ParticipantOrm, ProjectOrm, TicketHistoryEntryOrm, TicketOrm


class CommentMapper(ModelMapper[Comment, CommentOrm]):
    @staticmethod
    def to_entity(model: CommentOrm) -> Comment:
        attachment_mapper = AttachmentMapper()
        return Comment(
            id=model.id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            ticket_id=model.ticket_id,
            author_id=model.author_id,
            author_role=model.author_role,
            text=model.text,
            type=model.type,
            attachments=[
                attachment_mapper.to_entity(attachment) for attachment in model.attachments
            ],
        )

    @staticmethod
    def from_entity(entity: Comment) -> CommentOrm:
        attachment_mapper = AttachmentMapper()
        return CommentOrm(
            id=entity.id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            ticket_id=entity.ticket_id,
            author_id=entity.author_id,
            author_role=entity.author_role,
            text=entity.text,
            type=entity.type,
            attachments=[
                attachment_mapper.from_entity(attachment) for attachment in entity.attachments
            ],
        )


class TicketHistoryEntryMapper(ModelMapper[TicketHistoryEntry, TicketHistoryEntryOrm]):
    @staticmethod
    def to_entity(model: TicketHistoryEntryOrm) -> TicketHistoryEntry:
        return TicketHistoryEntry(
            id=model.id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            ticket_id=model.ticket_id,
            actor_id=model.actor_id,
            action=model.action,
            old_value=model.old_value,
            new_value=model.new_value,
            description=model.description,
        )

    @staticmethod
    def from_entity(entity: TicketHistoryEntry) -> TicketHistoryEntryOrm:
        return TicketHistoryEntryOrm(
            id=entity.id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            ticket_id=entity.ticket_id,
            actor_id=entity.actor_id,
            action=entity.action,
            old_value=entity.old_value,
            new_value=entity.new_value,
            description=entity.description,
        )


class TicketMapper(ModelMapper[Ticket, TicketOrm]):
    @staticmethod
    def to_entity(model: TicketOrm) -> Ticket:
        attachment_mapper = AttachmentMapper()
        comment_mapper = CommentMapper()
        history_mapper = TicketHistoryEntryMapper()
        return Ticket(
            id=model.id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            project_id=model.project_id,
            counterparty_id=model.counterparty_id,
            created_by_role=model.created_by_role,
            created_by=model.created_by,
            reporter_id=model.reporter_id,
            number=TicketNumber(model.number),
            title=model.title,
            description=model.description,
            status=model.status,
            priority=model.priority,
            assigned_to=model.assigned_to,
            closed_at=model.closed_at,
            tags=[Tag(name=tag["name"], color=tag["color"]) for tag in model.tags],
            comments=[comment_mapper.to_entity(comment) for comment in model.comments],
            attachments=[
                attachment_mapper.to_entity(attachment) for attachment in model.attachments
            ],
            history=[history_mapper.to_entity(entry) for entry in model.history]
        )

    @staticmethod
    def to_preview_entity(model: TicketOrm) -> Ticket:
        return Ticket(
            id=model.id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            project_id=model.project_id,
            counterparty_id=model.counterparty_id,
            created_by_role=model.created_by_role,
            created_by=model.created_by,
            reporter_id=model.reporter_id,
            number=TicketNumber(model.number),
            title=model.title,
            description=model.description,
            status=model.status,
            priority=model.priority,
            assigned_to=model.assigned_to,
            closed_at=model.closed_at,
            tags=[Tag(name=tag["name"], color=tag["color"]) for tag in model.tags],
            comments=[],
            attachments=[],
            history=[],
        )

    @staticmethod
    def from_entity(entity: Ticket) -> TicketOrm:
        attachment_mapper = AttachmentMapper()
        comment_mapper = CommentMapper()
        history_mapper = TicketHistoryEntryMapper()
        return TicketOrm(
            id=entity.id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            project_id=entity.project_id,
            counterparty_id=entity.counterparty_id,
            created_by_role=entity.created_by_role,
            created_by=entity.created_by,
            reporter_id=entity.reporter_id,
            number=entity.number.value,
            title=entity.title,
            description=entity.description,
            status=entity.status,
            priority=entity.priority,
            assigned_to=entity.assigned_to,
            closed_at=entity.closed_at,
            tags=[{"name": tag.name, "color": tag.color} for tag in entity.tags],
            comments=[comment_mapper.from_entity(comment) for comment in entity.comments],
            attachments=[
                attachment_mapper.from_entity(attachment) for attachment in entity.attachments
            ],
            history=[history_mapper.from_entity(entry) for entry in entity.history],
        )


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
            return Page.create_empty(params.page, params.size)

        # 2. Запрос для получения тикетов, с учётом фильтрации
        stmt = self._apply_filters(
            select(self.model), creator_id, counterparty_id, status, priority
        )
        stmt = stmt.order_by(self.model.created_at.desc()).offset(params.offset).limit(params.size)

        results = await self.session.execute(stmt)
        models = results.scalars().all()

        # 3. Для станицы не нашлось тикетов
        if not models:
            return Page(
                page=params.page,
                size=params.size,
                total_items=total_items,
                total_pages=(total_items + params.size - 1) // params.size,
                has_next=params.page * params.size < total_items,
                has_prev=params.page > 1,
                items=[],
            )

        # 4. Формирование страницы
        return Page(
            page=params.page,
            size=params.size,
            total_items=total_items,
            total_pages=(total_items + params.size - 1) // params.size,
            has_next=params.page * params.size < total_items,
            has_prev=params.page > 1,
            items=[self.model_mapper.to_preview_entity(model) for model in models],
        )


class ProjectMapper(ModelMapper[Project, ProjectOrm]):
    @staticmethod
    def to_entity(model: ProjectOrm) -> Project:
        return Project(
            id=model.id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            created_by=model.created_by,
            name=model.name,
            description=model.description,
            key=ProjectKey(model.key),
            counterparty_id=model.counterparty_id,
            owner_id=model.owner_id,
            status=model.status,
            participants=[
                Participant(
                    id=participant.id,
                    created_at=participant.created_at,
                    updated_at=participant.updated_at,
                    project_id=participant.project_id,
                    user_id=participant.user_id,
                    project_role=participant.project_role,
                    added_at=participant.added_at,
                    added_by=participant.added_by,
                )
                for participant in model.participants
            ]
        )

    @staticmethod
    def from_entity(entity: Project) -> ProjectOrm:
        return ProjectOrm(
            id=entity.id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            created_by=entity.created_by,
            name=entity.name,
            key=entity.key.value,
            description=entity.description,
            counterparty_id=entity.counterparty_id,
            owner_id=entity.owner_id,
            status=entity.status,
            participants=[
                ParticipantOrm(
                    id=participant.id,
                    created_at=participant.created_at,
                    updated_at=participant.updated_at,
                    user_id=participant.user_id,
                    project_id=participant.project_id,
                    project_role=participant.project_role,
                    added_at=participant.added_at,
                    added_by=participant.added_by,
                )
                for participant in entity.participants
            ]
        )


class SqlProjectRepository(SqlAlchemyRepository[Project, ProjectOrm]):
    model = ProjectOrm
    model_mapper = ProjectMapper

    async def get_by_key(self, project_key: ProjectKey) -> Project | None:
        stmt = select(self.model).where(self.model.key == project_key)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return None if model is None else self.model_mapper.to_entity(model)
