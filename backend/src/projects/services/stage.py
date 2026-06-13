from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ...iam.schemas import CurrentUser
from ...shared.domain.exceptions import NotFoundError
from ..domain.repos import ProjectRepository
from ..mappers import map_project_to_response
from ..schemas import ProjectResponse, ProjectStageCreate


class ProjectStageService:
    def __init__(self, session: AsyncSession, project_repo: ProjectRepository) -> None:
        self.session = session
        self.project_repo = project_repo

    async def create(
            self, project_id: UUID, data: ProjectStageCreate, current_user: CurrentUser
    ) -> ProjectResponse:
        project = await self.project_repo.read(project_id)
        if project is None:
            raise NotFoundError(f"Project with ID {project_id} not found")

        project.add_stage(
            name=data.name,
            description=data.description,
            order=data.order,
            planned_start=data.planned_start,
            planned_end=data.planned_end,
        )
        await self.project_repo.upsert(project)
        await self.session.commit()

        return map_project_to_response(project)
