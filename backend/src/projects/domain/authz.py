from src.iam.domain.authz import BaseAuthContext, PermissionResult, Principal
from src.iam.domain.entities import User

from .entities import Project
from .repos import ProjectMembershipRepository
from .rules import (
    AddMemberContext,
    AddMemberRule,
    CreateProjectRule,
    IsOwnerOrAdminRule,
    ManageProjectRule,
    ProjectContext,
)
from .vo import ProjectRole


class ProjectAuthZService:
    def __init__(self, membership_repo: ProjectMembershipRepository) -> None:
        self.membership_repo = membership_repo

    @staticmethod
    def can_create_project(principal: Principal) -> PermissionResult:
        ctx = BaseAuthContext(principal)
        return CreateProjectRule.check(ctx)

    @staticmethod
    def can_archive_project(principal: Principal, project: Project) -> PermissionResult:
        ctx = ProjectContext(principal=principal, project=project)
        return IsOwnerOrAdminRule.check(ctx)

    async def can_manage_project(self, principal: Principal, project: Project) -> PermissionResult:
        membership = await self.membership_repo.find(project.id, principal.id)
        ctx = ProjectContext(principal=principal, project=project, current_membership=membership)
        return ManageProjectRule.check(ctx)

    async def can_add_member(
            self,
            principal: Principal,
            project: Project,
            invitee: User,
            target_role: ProjectRole,
    ) -> PermissionResult:
        membership = await self.membership_repo.find(project.id, principal.id)
        ctx = AddMemberContext(
            principal=principal,
            project=project,
            current_membership=membership,
            invitee=invitee,
            target_role=target_role,
        )
        return AddMemberRule.check(ctx)

    def can_remove_member(self, principal: Principal, project: Project) -> PermissionResult:
        ...
