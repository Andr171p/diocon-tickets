from uuid import UUID

from fastapi import APIRouter, status

from src.iam.dependencies import CurrentSubjectDep

from ..dependencies import ProjectMemberServiceDep, ProjectServiceDep
from ..schemas import (
    NewProjectStagesOrder,
    ProjectResponse,
    ProjectStageCreate,
    ProjectStagePlan,
    ProjectStageResponse,
    ProjectStageUpdate,
)

router = APIRouter(prefix="/projects", tags=["Этапы проекта"])


@router.post(
    path="/{project_id}/stages",
    status_code=status.HTTP_201_CREATED,
    response_model=ProjectResponse,
    summary="Создать этап проекта"
)
async def create_project_stage(
        project_id: UUID,
        data: ProjectStageCreate,
        current_subject: CurrentSubjectDep,
        service: ProjectMemberServiceDep,
) -> ProjectResponse:
    return await service.add_member(project_id, data, current_subject)


@router.patch(
    path="/{project_id}/stages/{stage_id}",
    status_code=status.HTTP_200_OK,
    response_model=ProjectStageResponse,
    summary="Обновить этап проекта",
)
async def update_project_stage(
        project_id: UUID,
        stage_id: UUID,
        current_subject: CurrentSubjectDep,
        data: ProjectStageUpdate,
        service: ProjectServiceDep,
) -> ProjectStageResponse:
    return await service.edit_stage(
        project_id=project_id,
        stage_id=stage_id,
        data=data,
        current_subject=current_subject,
    )


@router.patch(
    path="/{project_id}/stages/order",
    status_code=status.HTTP_200_OK,
    response_model=ProjectResponse,
    summary="Изменить порядок проведения этапов",
)
async def reorder_project_stages(
        project_id: UUID,
        new_order: NewProjectStagesOrder,
        current_subject: CurrentSubjectDep,
        service: ProjectServiceDep,
) -> ProjectResponse:
    return await service.reorder_stages(
        project_id=project_id,
        new_order=new_order,
        current_subject=current_subject,
    )


@router.delete(
    path="/{project_id}/stages/{stage_id}",
    status_code=status.HTTP_200_OK,
    response_model=ProjectResponse,
    summary="Удалить этап из проекта"
)
async def delete_project_stage(
        project_id: UUID,
        stage_id: UUID,
        current_subject: CurrentSubjectDep,
        service: ProjectServiceDep,
) -> ProjectResponse:
    return await service.remove_stage(
        project_id=project_id,
        stage_id=stage_id,
        current_subject=current_subject,
    )


@router.post(
    path="/{project_id}/stages/{stage_id}/start",
    status_code=status.HTTP_200_OK,
    response_model=ProjectResponse,
    summary="Начать этап проекта"
)
async def start_project_stage(
        project_id: UUID,
        stage_id: UUID,
        current_subject: CurrentSubjectDep,
        service: ProjectServiceDep,
) -> ProjectResponse:
    return await service.start_stage(
        project_id=project_id, stage_id=stage_id, current_subject=current_subject
    )


@router.post(
    path="/{project_id}/stages/{stage_id}/complete",
    status_code=status.HTTP_200_OK,
    response_model=ProjectResponse,
    summary="Завершить этап проекта"
)
async def complete_project_stage(
        project_id: UUID,
        stage_id: UUID,
        current_subject: CurrentSubjectDep,
        service: ProjectServiceDep,
) -> ProjectResponse:
    return await service.complete_stage(
        project_id=project_id, stage_id=stage_id, current_subject=current_subject
    )


@router.post(
    path="/{project_id}/stages/{stage_id}/skip",
    status_code=status.HTTP_200_OK,
    response_model=ProjectResponse,
    summary="Пропустить этап проекта"
)
async def skip_project_stage(
        project_id: UUID,
        stage_id: UUID,
        current_subject: CurrentSubjectDep,
        service: ProjectServiceDep,
) -> ProjectResponse:
    return await service.complete_stage(
        project_id=project_id, stage_id=stage_id, current_subject=current_subject,
    )


@router.patch(
    path="/{project_id}/stages/{stage_id}/schedule",
    status_code=status.HTTP_200_OK,
    response_model=ProjectStageResponse,
    summary="Запланировать проведение этапа",
)
async def schedule_project_stage(
        project_id: UUID,
        stage_id: UUID,
        data: ProjectStagePlan,
        current_subject: CurrentSubjectDep,
        service: ProjectServiceDep,
) -> ProjectStageResponse:
    return await service.schedule_stage(
        project_id=project_id,
        stage_id=stage_id,
        data=data,
        current_subject=current_subject,
    )
