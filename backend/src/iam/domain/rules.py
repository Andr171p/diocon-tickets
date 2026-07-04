from typing import ClassVar

from .authz import PermissionResult, Subject, SubjectType
from .entities import Invitation, User
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

        return PermissionResult(False, "Required staff user")


class IsCustomerRule:
    ALLOWED_USER_ROLES: ClassVar[set[UserRole]] = {UserRole.CUSTOMER, UserRole.CUSTOMER_ADMIN}

    def __init__(self, subject: Subject | User) -> None:
        self.subject = subject

    def check(self) -> PermissionResult:
        for user_role in self.ALLOWED_USER_ROLES:
            if self.subject.has_role(user_role):
                return PermissionResult(True)

        return PermissionResult(False, "Required customer user")


class IsUserRule:
    def __init__(self, subject: Subject) -> None:
        self.subject = subject

    def check(self) -> PermissionResult:
        if self.subject.type == SubjectType.USER:
            return PermissionResult(True)

        return PermissionResult(False, "You are not user")


class IsInviterRule:
    def __init__(self, subject: Subject, invitation: Invitation) -> None:
        self.subject = subject
        self.invitation = invitation

    def check(self) -> PermissionResult:
        if self.invitation.invited_by != self.subject.id:
            return PermissionResult(False, "You are not inviter of this invitation")

        return PermissionResult(True)
