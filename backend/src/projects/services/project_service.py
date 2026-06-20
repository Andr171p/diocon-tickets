import random
import string
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.iam.domain.authz import Subject
from src.iam.domain.exceptions import PermissionDeniedError
from src.iam.domain.repos import UserRepository
from src.shared.domain.events import EventPublisher
from src.shared.domain.exceptions import AlreadyExistsError, NotFoundError
from src.shared.schemas import Page

from ..domain.authz import ProjectAuthZService
from ..domain.entities import Project
from ..domain.repos import ProjectMembershipRepository, ProjectRepository
from ..domain.vo import ProjectKey, ProjectRole
from ..mappers import (
    map_membership_to_response,
    map_project_to_detailed_response,
    map_project_to_response,
)
from ..schemas import (
    KeyCheckResult,
    ProjectCreate,
    ProjectDetailedResponse,
    ProjectMembershipCreate,
    ProjectMembershipResponse,
    ProjectResponse,
    ProjectStageCreate,
)


class ProjectService:
    def __init__(
            self,
            session: AsyncSession,
            project_repo: ProjectRepository,
            membership_repo: ProjectMembershipRepository,
            user_repo: UserRepository,
            event_publisher: EventPublisher,
    ) -> None:
        self.session = session
        self.user_repo = user_repo
        self.project_repo = project_repo
        self.membership_repo = membership_repo
        self.authz_service = ProjectAuthZService(membership_repo)
        self.event_publisher = event_publisher

    async def generate_key_suggestions(
            self, original_key: str, max_attempts: int = 5, min_key_length: int = 3
    ) -> list[str]:
        """
        Генерация списка альтернативных ключей проекта в стиле Jira.
        Для избежания коллизий при создании проекта.

        Примеры:
         - original_key = "WEB" -> ["WEB1", "WEB2", "WEB3", "WEB-1", "WEB-2", ...]
         - original_key = "CRM" -> ["CRM1", "CRM2", "CRM3", ...]
        """

        base_key = original_key.strip().upper()

        if not base_key:
            base_key = "PROJ"  # fallback

        # Добавление простых числовых суффиксов
        suggestions = [f"{base_key}{i}" for i in range(1, max_attempts + 1)]

        # Если ключ короткий, то добавление вариантов с буквами
        if len(base_key) <= min_key_length:
            alphabet = string.ascii_uppercase
            suggestions.extend(
                f"{base_key}{letter}" for letter in random.sample(alphabet, len(alphabet))
            )

        # Удаление дубликатов и сохранение порядка
        seen = set()
        unique_suggestions = []
        for suggestion in suggestions:
            if suggestion not in seen:
                seen.add(suggestion)
                unique_suggestions.append(suggestion)

        unique_suggestions = unique_suggestions[:max_attempts * 2]
        existing_keys = await self.project_repo.get_existing_keys(unique_suggestions)
        available = [key for key in unique_suggestions if key not in existing_keys]

        return available[:max_attempts]

    async def check_key(self, key: str) -> KeyCheckResult:
        """Проверка ключа на уникальность перед созданием"""

        key = ProjectKey(key)
        project = await self.project_repo.get_by_key(key)
        if project is None:
            return KeyCheckResult(available=True)

        suggestions = await self.generate_key_suggestions(key.value)
        return KeyCheckResult(available=False, suggestions=suggestions)

    async def create(
            self, data: ProjectCreate, current_subject: Subject, max_attempts: int = 5,
    ) -> ProjectDetailedResponse:
        """
        Создание проекта с уникальным ключом
        """

        permission = self.authz_service.can_create_project(current_subject)
        if not permission.allowed:
            raise PermissionDeniedError(permission.reason)

        original_key, key_candidate = data.key, data.key
        for attempt in range(1, max_attempts + 1):
            try:
                project = Project.create(
                    name=data.name,
                    key=key_candidate,
                    description=data.description,
                    counterparty_id=data.counterparty_id,
                    created_by=current_subject.id,
                )
                await self.project_repo.create(project)
                await self.session.flush()

            except IntegrityError:
                await self.session.rollback()
                key_candidate = f"{original_key}{attempt}"

            else:
                owner = project.create_membership(
                    user_id=current_subject.id,
                    project_role=ProjectRole.OWNER,
                    created_by=current_subject.id,
                )
                await self.membership_repo.create(owner)
                await self.session.commit()

                for event in project.collect_events():
                    await self.event_publisher.publish(event)

                memberships = [owner]
                return map_project_to_detailed_response(
                    project, memberships=Page.create(
                        memberships, total_items=len(memberships), page=1, size=1,
                    )
                )

        raise AlreadyExistsError(
            f"Project with key - {key_candidate} already exists. "
            f"{max_attempts} attempts were not enough to resolve the uniqueness of the key. "
            f"Try again with a different key.",
            details={"last_suggested_key": key_candidate},
        )

    async def add_member(
            self, project_id: UUID, data: ProjectMembershipCreate, current_subject: Subject
    ) -> ProjectMembershipResponse:
        """Добавление участника в проект"""

        project = await self.project_repo.read(project_id)
        if project is None:
            raise NotFoundError(f"Project with ID {project_id} not found")

        invitee = await self.user_repo.read(data.user_id)
        if invitee is None or invitee.is_deleted:
            raise NotFoundError(f"User with ID {data.user_id} not found")

        permission = await self.authz_service.can_add_member(
            subject=current_subject,
            project=project,
            invitee=invitee,
            target_role=data.project_role,
        )
        if not permission.allowed:
            raise PermissionDeniedError(permission.reason)

        existing = await self.membership_repo.find(project_id, data.user_id)
        if existing is not None:
            raise AlreadyExistsError(f"User with ID {data.user_id} is already a member")

        membership = project.create_membership(
            user_id=data.user_id,
            project_role=data.project_role,
            created_by=current_subject.id,
        )
        await self.membership_repo.create(membership)
        await self.session.commit()

        for event in project.collect_events():
            await self.event_publisher.publish(event)

        return map_membership_to_response(membership)

    async def remove_member(
            self, project_id: UUID, user_id: UUID, current_subject: Subject
    ) -> None:
        """Удаляет участника из проекта"""

        project = await self.project_repo.read(project_id)
        if project is None:
            raise NotFoundError(f"Project with ID {project_id} not found")

        membership_to_remove = await self.membership_repo.find(project_id, user_id)
        if membership_to_remove is None:
            raise NotFoundError(
                f"User with ID {user_id} not a member of the project with ID {project_id}"
            )

        permission = await self.authz_service.can_remove_member(
            subject=current_subject,
            project=project,
            membership_to_remove=membership_to_remove,
        )
        if not permission.allowed:
            raise PermissionDeniedError(permission.reason)

        membership_to_remove.remove(removed_by=current_subject.id)
        await self.membership_repo.update(membership_to_remove)
        await self.session.commit()

        for event in membership_to_remove.collect_events():
            await self.event_publisher.publish(event)

    async def archive(self, project_id: UUID, current_subject: Subject) -> ProjectResponse:
        """
        Архивирование проекта (soft delete метод).
        """

        project = await self.project_repo.read(project_id)
        if project is None:
            raise NotFoundError(f"Project with ID {project_id} not found")

        permission = self.authz_service.can_archive_project(
            subject=current_subject, project=project,
        )
        if not permission.allowed:
            raise PermissionDeniedError(permission.reason)

        project.archive(archived_by=current_subject.id)
        await self.project_repo.update(project)
        await self.session.commit()

        for event in project.collect_events():
            await self.event_publisher.publish(event)

        return map_project_to_response(project)

    async def add_stage(
            self, project_id: UUID, data: ProjectStageCreate, current_subject: Subject
    ) -> ProjectResponse:
        """
        Добавить новый этап в проект.
        """

        project = await self.project_repo.read(project_id)
        if project is None:
            raise NotFoundError(f"Project with ID {project_id} not found")

        permission = await self.authz_service.can_manage_project(
            subject=current_subject, project=project
        )
        if not permission.allowed:
            raise PermissionDeniedError(permission.reason)

        project.add_stage(
            name=data.name,
            description=data.description,
            order=data.order,
            planned_start=data.planned_start,
            planned_end=data.planned_end,
        )
        await self.project_repo.update(project)
        await self.session.commit()

        return map_project_to_response(project)
