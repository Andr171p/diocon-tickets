from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from src.iam.domain.authz import Subject
from src.iam.domain.entities import User
from src.iam.domain.exceptions import PermissionDeniedError
from src.iam.domain.repos import UserRepository
from src.shared.domain.repos import get_or_raise_404
from src.shared.utils.time import current_datetime

from ..domain.authz import ProjectAuthZService
from ..domain.entities import Project, ProjectStage
from ..domain.repos import ProjectMemberRepository, ProjectRepository


@dataclass(frozen=True)
class ProjectStageReportRow:
    """
    Строка отчёта по одному этапу проекта.
    """

    number: int
    name: str
    status: str
    planned_start: str
    planned_end: str
    started_at: str
    completed_at: str
    responsible: str
    is_overdue: str
    planned_duration_days: str
    description: str
    completion_criteria: str


@dataclass(frozen=True)
class ProjectStagesReport:
    """
    Данные отчёта по этапам проекта в формате, независимом от типа файла.
    """

    project_id: UUID
    project_name: str
    project_key: str
    project_url: str
    project_status: str
    generated_at: datetime
    rows: list[ProjectStageReportRow]


class ProjectStageExportService:
    """
    Сервис для подготовки отчёта по этапам проекта.
    """

    def __init__(
        self,
        project_repo: ProjectRepository,
        member_repo: ProjectMemberRepository,
        user_repo: UserRepository,
        frontend_url: str,
    ) -> None:
        self.project_repo = project_repo
        self.user_repo = user_repo
        self.frontend_url = frontend_url.rstrip("/")
        self.authz_service = ProjectAuthZService(member_repo)

    async def build_report(
        self,
        project_id: UUID,
        current_subject: Subject,
    ) -> ProjectStagesReport:
        """
        Собрать данные отчёта по этапам проекта.
        """

        project = await get_or_raise_404(self.project_repo.read, project_id, Project)

        permission = await self.authz_service.can_export_project(
            subject=current_subject,
            project_id=project_id,
        )
        if not permission.allowed:
            raise PermissionDeniedError(permission.reason)

        stages = sorted(project.stages, key=lambda stage: stage.execution_order)
        responsible_users = await self._get_responsible_users(stages)

        return ProjectStagesReport(
            project_id=project.id,
            project_name=project.name,
            project_key=project.key.value,
            project_url=f"{self.frontend_url}/projects/{project.key.value}",
            project_status=project.status.value,
            generated_at=current_datetime(),
            rows=[
                self._map_stage_to_row(
                    number=index,
                    stage=stage,
                    responsible_users=responsible_users,
                )
                for index, stage in enumerate(stages, start=1)
            ],
        )

    async def _get_responsible_users(
        self,
        stages: list[ProjectStage],
    ) -> dict[UUID, User]:
        responsible_ids = {
            stage.responsible_id for stage in stages if stage.responsible_id is not None
        }

        users: dict[UUID, User] = {}
        for user_id in responsible_ids:
            user = await self.user_repo.read(user_id)
            if user is not None:
                users[user_id] = user

        return users

    @classmethod
    def _map_stage_to_row(
        cls,
        number: int,
        stage: ProjectStage,
        responsible_users: dict[UUID, User],
    ) -> ProjectStageReportRow:
        return ProjectStageReportRow(
            number=number,
            name=stage.name,
            status=stage.status.value,
            planned_start=cls._format_date(stage.planned_start),
            planned_end=cls._format_date(stage.planned_end),
            started_at=cls._format_datetime(stage.started_at),
            completed_at=cls._format_datetime(stage.completed_at),
            responsible=cls._format_responsible(stage.responsible_id, responsible_users),
            is_overdue="Да" if stage.is_overdue else "Нет",
            planned_duration_days=cls._format_int(stage.planned_duration_days),
            description=stage.description or "-",
            completion_criteria=cls._format_list(stage.completion_criteria),
        )

    @staticmethod
    def _format_responsible(
        responsible_id: UUID | None,
        responsible_users: dict[UUID, User],
    ) -> str:
        if responsible_id is None:
            return "-"

        user = responsible_users.get(responsible_id)
        if user is None:
            return str(responsible_id)

        if user.full_name is not None:
            return user.full_name.value

        if user.username is not None:
            return user.username.value

        return user.email.value

    @staticmethod
    def _format_date(value: date | None) -> str:
        if value is None:
            return "-"

        return value.strftime("%d.%m.%Y")

    @staticmethod
    def _format_datetime(value: datetime | None) -> str:
        if value is None:
            return "-"

        return value.strftime("%d.%m.%Y %H:%M")

    @staticmethod
    def _format_int(value: int | None) -> str:
        if value is None:
            return "-"

        return str(value)

    @staticmethod
    def _format_list(value: list[str]) -> str:
        if not value:
            return "-"

        return "\n".join(value)
