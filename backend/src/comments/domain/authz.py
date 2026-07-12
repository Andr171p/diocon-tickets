from src.iam.domain.authz import AllOf, AnyOf, Not, PermissionResult, Subject
from src.iam.domain.rules import IsAdminRule, IsCustomerRule, IsStaffRule

from .entities import Comment
from .rules import IsCommentAuthorRule, IsNoteVisibilityRule
from .vo import CommentVisibility


def can_create_comment(subject: Subject, visibility: CommentVisibility) -> PermissionResult:
    customer_rule = AllOf(IsCustomerRule(subject), Not(IsNoteVisibilityRule(visibility)))
    staff_rule = IsStaffRule(subject)

    return AnyOf(customer_rule, staff_rule).check()


def can_edit_or_remove_comment(subject: Subject, comment: Comment) -> PermissionResult:
    rules = [IsAdminRule(subject), IsCommentAuthorRule(subject, comment)]
    return AnyOf(*rules).check()
