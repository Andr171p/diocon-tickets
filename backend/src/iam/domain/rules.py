from typing import ClassVar

from .authz import PermissionResult, Subject, SubjectType
from .entities import User
from .vo import UserRole


class IsAdminRule:
    def __init__(self, subject: Subject) -> None:
        self.subject = subject

    def check(self) -> PermissionResult:
        if self.subject.has_role(UserRole.ADMIN):
            return PermissionResult(True)

        return PermissionResult(False, "Admin required")


class IsStaffRule:
    ALLOWED_USER_ROLES: ClassVar[set[UserRole]] = {
        UserRole.ADMIN,
        UserRole.SUPPORT_MANAGER,
        UserRole.SUPPORT_AGENT,
        UserRole.DEVELOPER,
        UserRole.FINANCE,
        UserRole.ACCOUNT_MANAGER,
    }

    def __init__(self, subject: Subject | User) -> None:
        self.subject = subject

    def check(self) -> PermissionResult:
        for user_role in self.ALLOWED_USER_ROLES:
            if self.subject.has_role(user_role):
                return PermissionResult(True)

        return PermissionResult(False, "Only staff can create tasks")


class IsUserRule:
    def __init__(self, subject: Subject) -> None:
        self.subject = subject

    def check(self) -> PermissionResult:
        if self.subject.type == SubjectType.USER:
            return PermissionResult(True)

        return PermissionResult(False, "You are not user")
