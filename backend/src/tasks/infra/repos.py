from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from ...media.infra.repo import AttachmentMapper
from ...shared.infra.repos import ModelMapper, SqlAlchemyRepository
from ...shared.schemas import Page, Pagination
from ..domain.entities import Task
from ..domain.repos import TaskView
from ..domain.vo import StoryPoints, TaskNumber, TaskStatus
from .models import TaskOrm, TaskSequence


class TaskMapper(ModelMapper[Task, TaskOrm]):
    @staticmethod
    def to_entity(model: TaskOrm) -> Task:
        return Task(
            id=model.id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
            ticket_id=model.ticket_id,
            project_id=model.project_id,
            number=TaskNumber(model.number),
            title=model.title,
            description=model.description,
            status=model.status,
            priority=model.priority,
            story_points=StoryPoints(model.story_points),
            assignee_id=model.assignee_id,
            reviewer_id=model.reviewer_id,
            estimated_hours=Decimal(model.estimated_hours),
            actual_hours=Decimal(model.actual_hours),
            due_date=model.due_date,
            started_at=model.started_at,
            completed_at=model.completed_at,
            created_by=model.created_by,
            attachments=[
                AttachmentMapper.to_entity(attachment) for attachment in model.attachments
            ],
        )

    @staticmethod
    def from_entity(entity: Task) -> TaskOrm:
        return TaskOrm(
            id=entity.id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            deleted_at=entity.deleted_at,
            ticket_id=entity.ticket_id,
            project_id=entity.project_id,
            number=entity.number.value,
            title=entity.title,
            description=entity.description,
            status=entity.status,
            priority=entity.priority,
            story_points=entity.story_points.value,
            assignee_id=entity.assignee_id,
            reviewer_id=entity.reviewer_id,
            estimated_hours=float(entity.estimated_hours),
            actual_hours=float(entity.actual_hours),
            due_date=entity.due_date,
            started_at=entity.started_at,
            completed_at=entity.completed_at,
            created_by=entity.created_by,
        )

    @staticmethod
    def to_view(model: TaskOrm) -> TaskView:
        return TaskView(
            id=model.id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            number=TaskNumber(model.number),
            title=model.title,
            status=model.status,
            priority=model.priority,
            assignee_id=model.assignee_id,
            due_date=model.due_date,
            story_points=Decimal(model.story_points),
            project_id=model.project_id,
            ticket_id=model.ticket_id,
        )


class SqlTaskRepository(SqlAlchemyRepository[Task, TaskOrm]):
    model = TaskOrm
    model_mapper = TaskMapper

    async def get_by_number(self, number: TaskNumber) -> Task | None:
        stmt = select(self.model).where(self.model.number == number.value)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return None if model is None else self.model_mapper.to_entity(model)

    async def get_next_sequence(
            self, ticket_id: UUID | None = None, project_id: UUID | None = None
    ) -> int:
        # Атомарная операция для получения последовательности
        stmt = (
            pg_insert(TaskSequence)
            .values(project_id=project_id, ticket_id=ticket_id, last_number=1)
            .on_conflict_do_update(
                constraint="uq_task_sequences",
                set_={"last_number": TaskSequence.last_number + 1},
            )
            .returning(TaskSequence.last_number)
        )

        result = await self.session.execute(stmt)

        return result.scalar_one()

    async def read_views(
            self,
            pagination: Pagination,
            *,
            status: TaskStatus | None = None,
            project_id: UUID | None = None,
            ticket_id: UUID | None = None,
            assignee_id: UUID | None = None,
    ) -> Page[TaskView]:
        # 1. Базовый запрос
        stmt = select(self.model).where(self.model.deleted_at.is_not(None))

        # 2. Применение фильтров
        if status is not None:
            stmt = stmt.where(self.model.status == status)
        if project_id is not None:
            stmt = stmt.where(self.model.project_id == project_id)
        if ticket_id is not None:
            stmt = stmt.where(self.model.ticket_id == ticket_id)
        if assignee_id is not None:
            stmt = stmt.where(self.model.assignee_id == assignee_id)

        # 3. Получение общего количества относительно применённых фильтров
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_items = await self.session.scalar(count_stmt)
        if total_items == 0:
            return Page.create([], total_items, pagination.page, pagination.size)

        # 4. Получение указанной страницы
        stmt = (
            stmt.order_by(self.model.created_at.desc())
            .offset(pagination.offset)
            .limit(pagination.size)
        )
        results = await self.session.execute(stmt)
        models = results.scalars().all()

        return Page.create(
            items=[self.model_mapper.to_view(model) for model in models],
            total_items=total_items,
            page=pagination.page,
            size=pagination.size,
        )
