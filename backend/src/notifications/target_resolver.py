from uuid import UUID

from ..iam.domain.repos import UserRepository
from ..tickets.domain.events import TicketCreated
from ..tickets.domain.repos import ProjectRepository
from ..tickets.domain.vo import ProjectRole


class NotificationTargetResolver:
    """
    Отвечает за определение получателей уведомлений
    """

    def __init__(self, project_repo: ProjectRepository, user_repo: UserRepository) -> None:
        self.project_repo = project_repo
        self.user_repo = user_repo

    async def get_target_for_ticket_created(self, event: TicketCreated) -> list[UUID]:
        """
        Определение пользователей, которые должны получить уведомление о создании тикета
        """

        targets: set[UUID] = set()

        # 1. Инициатор всегда получает уведомление
        targets.add(event.reporter_id)

        # 2. Если есть проект - уведомления для поддержки проекта
        if event.project_id is not None:
            project = await self.project_repo.read(event.project_id)
            if project is not None:
                for membership in project.memberships:
                    if membership.is_active and membership.project_role in {
                        ProjectRole.OWNER, ProjectRole.MANAGER, ProjectRole.MEMBER
                    }:
                        targets.add(membership.user_id)

        # 3. Иначе - уведомляются все сотрудники поддержки
        else:
            support_ids = await self.user_repo.get_all_support_ids()
            targets.update(support_ids)

        return list(targets)
