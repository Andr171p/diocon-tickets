from ...iam.domain.exceptions import PermissionDeniedError
from ...iam.schemas import CurrentUser
from ...projects.domain.services import ProjectAccessService
from ...shared.schemas import Pagination
from ..domain.acl import can_view_tasks
from ..domain.constants import TASK_STATUS_LABEL_MAP
from ..domain.repos import TaskRepository
from ..mappers import map_task_view_to_response
from ..schemas import (
    KanbanBoard,
    KanbanColumn,
    KanbanContextType,
    KanbanFilters,
)


class TaskBoardService:
    def __init__(
            self, task_repo: TaskRepository, project_access_service: ProjectAccessService
    ) -> None:
        self.task_repo = task_repo
        self.project_access_service = project_access_service

    async def get_kanban_board(
            self,
            pagination: Pagination,
            context: KanbanContextType,
            filters: KanbanFilters,
            current_user: CurrentUser,
    ) -> KanbanBoard:
        """Получение канбан доски с задачами"""

        # 1. Проверка прав на просмотр задач
        permission = can_view_tasks(current_user.role)
        if not permission.allowed:
            raise PermissionDeniedError(permission.reason)

        # 2. Определение контекста задач
        kwargs = {}
        if context.type == "project":

            # 2.1 Проверка прав на просмотр задач в проекте
            permission = await self.project_access_service.can_view_tasks(
                project_id=context.project_id,
                user_id=current_user.user_id,
                user_role=current_user.role,
            )
            if not permission.allowed:
                raise PermissionDeniedError(permission.reason)

            kwargs = {"project_id": context.project_id}

        elif context.type == "ticket":
            kwargs = {"ticket_id": context.ticket_id}

        elif context.type == "assignee":
            kwargs = {"assignee_id": context.assignee_id}

        elif context.type == "my":
            kwargs = {"assignee_id": current_user.user_id}

        kwargs.update({"priorities": filters.priorities, "overdue_only": filters.overdue_only})

        # 3. Формирование канбан доски
        groups = await self.task_repo.get_grouped_by_status(pagination, **kwargs)

        columns = [
            KanbanColumn(
                status=status,
                label=TASK_STATUS_LABEL_MAP[status],
                tasks=tasks_page.to_response(map_task_view_to_response),
            )
            for status, tasks_page in groups.items()
        ]

        # 4. Общее количество задач с учётом контекста
        total_tasks = sum(column.tasks.total_items for column in columns)

        return KanbanBoard(context=context, columns=columns, total_tasks=total_tasks)
