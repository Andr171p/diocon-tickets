from decimal import Decimal
from uuid import UUID

from sqlalchemy import and_, func, select

from ...media.infra.repo import AttachmentMapper
from ...shared.infra.repos import ModelMapper, SqlAlchemyRepository
from ..domain.entities import Task
from ..domain.vo import StoryPoints, TaskNumber
from .models import TaskOrm


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


class SqlTaskRepository(SqlAlchemyRepository[Task, TaskOrm]):
    model = TaskOrm
    model_mapper = TaskMapper

    async def get_by_number(self, number: TaskNumber) -> Task | None:
        stmt = select(self.model).where(self.model.number == number)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return None if model is None else self.model_mapper.to_entity(model)

    async def get_next_sequence(
            self, ticket_id: UUID | None = None, project_id: UUID | None = None
    ) -> int:
        conditions = []

        # 1. Применение фильтров в зависимости от переданного пространства имён
        if ticket_id is not None:
            conditions.append(self.model.ticket_id == ticket_id)
            if project_id is not None:
                conditions.append(self.model.project_id == project_id)
        elif project_id is not None and ticket_id is None:
            conditions.extend((
                self.model.project_id == project_id, self.model.ticket_id.is_(None),
            ))
        else:
            conditions.extend((
                self.model.project_id.is_(None), self.model.ticket_id.is_(None),
            ))

        # 2. Запрос с применением фильтров
        stmt = select(func.count()).select_from(self.model).where(and_(*conditions))

        # 3. Выполнение запроса с блокировкой для предотвращения race condition
        stmt = stmt.with_for_update()
        result = await self.session.scalar(stmt) or 0

        return int(result) + 1
