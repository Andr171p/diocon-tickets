from ..media.mappers import map_attachment_to_response
from .domain.entities import Task
from .schemas import TaskResponse


def map_task_to_response(task: Task) -> TaskResponse:
    return TaskResponse(
        id=task.id,
        created_at=task.created_at,
        updated_at=task.updated_at,
        is_archived=task.is_deleted,
        title=task.title,
        description=task.description,
        priority=task.priority,
        status=task.status,
        assignee_id=task.assignee_id,
        reviewer_id=task.reviewer_id,
        estimated_hours=None if task.estimated_hours is None else float(task.estimated_hours),
        actual_hours=float(task.actual_hours),
        due_date=task.due_date,
        started_at=task.started_at,
        completed_at=task.completed_at,
        created_by=task.created_by,
        attachments=[map_attachment_to_response(attachment) for attachment in task.attachments],
    )
