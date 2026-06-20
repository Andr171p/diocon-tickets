from src.iam.domain.authz import BaseAuthContext, PermissionResult, Subject
from src.iam.domain.entities import User

from .entities import Project, ProjectMembership
from .repos import ProjectMembershipRepository
from .rules import (
    AddMemberContext,
    AddMemberRule,
    CreateProjectRule,
    IsOwnerOrAdminRule,
    ManageProjectRule,
    ProjectContext,
    RemoveMemberContext,
    RemoveMemberRule,
)
from .vo import ProjectRole


class ProjectAuthZService:
    def __init__(self, membership_repo: ProjectMembershipRepository) -> None:
        self.membership_repo = membership_repo

    @staticmethod
    def can_create_project(subject: Subject) -> PermissionResult:
        ctx = BaseAuthContext(subject)
        return CreateProjectRule.check(ctx)

    @staticmethod
    def can_archive_project(subject: Subject, project: Project) -> PermissionResult:
        ctx = ProjectContext(subject=subject, project=project)
        return IsOwnerOrAdminRule.check(ctx)

    async def can_manage_project(self, subject: Subject, project: Project) -> PermissionResult:
        membership = await self.membership_repo.find(project.id, subject.id)
        ctx = ProjectContext(subject=subject, project=project, current_membership=membership)
        return ManageProjectRule.check(ctx)

    async def can_add_member(
            self,
            subject: Subject,
            project: Project,
            invitee: User,
            target_role: ProjectRole,
    ) -> PermissionResult:
        membership = await self.membership_repo.find(project.id, subject.id)
        ctx = AddMemberContext(
            subject=subject,
            project=project,
            current_membership=membership,
            invitee=invitee,
            target_role=target_role,
        )
        return AddMemberRule.check(ctx)

    async def can_remove_member(
            self, subject: Subject, project: Project, membership_to_remove: ProjectMembership
    ) -> PermissionResult:
        membership = await self.membership_repo.find(project.id, subject.id)
        ctx = RemoveMemberContext(
            subject=subject,
            project=project,
            current_membership=membership,
            membership_to_remove=membership_to_remove,
        )
        return RemoveMemberRule.check(ctx)
