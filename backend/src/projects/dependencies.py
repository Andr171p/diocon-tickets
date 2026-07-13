from typing import Annotated

from uuid import UUID

from fastapi import Depends, Query

from src.iam.dependencies import CurrentSubjectDep, UserRepoDep
from src.shared.dependencies import EventPublisherDep, PaginationDep, SessionDep
from src.shared.domain.exceptions import NotFoundError
from src.shared.schemas import Page

from .domain.repos import ProjectMemberRepository, ProjectRepository
from .infra.repos import SqlProjectMemberRepository, SqlProjectRepository
from .mappers import map_member_to_response, map_project_to_response
from .schemas import ProjectMemberResponse, ProjectResponse
from .services import ProjectMemberService, ProjectService


def get_project_repo(session: SessionDep) -> SqlProjectRepository:
    return SqlProjectRepository(session)


def get_project_member_repo(session: SessionDep) -> SqlProjectMemberRepository:
    return SqlProjectMemberRepository(session)


ProjectRepoDep = Annotated[ProjectRepository, Depends(get_project_repo)]
ProjectMemberRepoDep = Annotated[ProjectMemberRepository, Depends(get_project_member_repo)]


def get_project_service(
        session: SessionDep,
        project_repo: ProjectRepoDep,
        membership_repo: ProjectMemberRepoDep,
        event_publisher: EventPublisherDep,
) -> ProjectService:
    return ProjectService(
        uow=session,
        project_repo=project_repo,
        member_repo=membership_repo,
        event_publisher=event_publisher,
    )


def get_project_member_service(
        session: SessionDep,
        project_repo: ProjectRepoDep,
        user_repo: UserRepoDep,
        member_repo: ProjectMemberRepoDep,
        event_publisher: EventPublisherDep,
) -> ProjectMemberService:
    return ProjectMemberService(
        uow=session,
        project_repo=project_repo,
        user_repo=user_repo,
        member_repo=member_repo,
        event_publisher=event_publisher,
    )


ProjectServiceDep = Annotated[ProjectService, Depends(get_project_service)]
ProjectMemberServiceDep = Annotated[ProjectMemberService, Depends(get_project_member_service)]


async def get_project_or_404(project_id: UUID, project_repo: ProjectRepoDep) -> ProjectResponse:
    project = await project_repo.read(project_id)
    if project is None:
        raise NotFoundError(f"Project with ID {project_id} not found")

    return map_project_to_response(project)


async def paginate_projects(
        pagination: PaginationDep, project_repo: ProjectRepoDep
) -> Page[ProjectResponse]:
    page = await project_repo.paginate(pagination)
    return page.to_response(map_project_to_response)


async def paginate_my_projects(
        current_subject: CurrentSubjectDep,
        pagination: PaginationDep,
        project_repo: ProjectRepoDep,
        owner_only: Annotated[
            bool, Query(description="Только те, где пользователь владелец")
        ] = False,
) -> Page[ProjectResponse]:
    page = await project_repo.get_by_user_membership(
        user_id=current_subject.id,
        pagination=pagination,
        owner_only=owner_only,
    )
    return page.to_response(map_project_to_response)


async def get_member_or_404(
        project_id: UUID, user_id: UUID, member_repo: ProjectMemberRepoDep,
) -> ProjectMemberResponse:
    member = await member_repo.find(project_id, user_id)
    if member is None:
        raise NotFoundError(f"Member {user_id} does not exist in project {project_id}")

    return map_member_to_response(member)


async def paginate_members(
        project_id: UUID, pagination: PaginationDep, member_repo: ProjectMemberRepoDep,
) -> Page[ProjectMemberResponse]:
    page = await member_repo.paginate(pagination, project_id=project_id)
    return page.to_response(map_member_to_response)
