from ...iam.schemas import CurrentUser
from ...shared.schemas import Pagination
from ..domain.consts import TASK_STATUS_LABEL_MAP
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
            self, task_repo: TaskRepository
    ) -> None:
        self.task_repo = task_repo

    async def get_kanban_board(
            self,
            pagination: Pagination,
            context: KanbanContextType,
            filters: KanbanFilters,
            current_user: CurrentUser,
    ) -> KanbanBoard:
        """Получение канбан доски с задачами"""

        # 2. Определение контекста задач
        kwargs = {}
        if context.type == "project":

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
