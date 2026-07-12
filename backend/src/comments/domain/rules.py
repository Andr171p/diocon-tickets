from src.iam.domain.authz import PermissionResult, Subject

from .entities import Comment
from .vo import CommentVisibility


class IsNoteVisibilityRule:
    def __init__(self, visibility: CommentVisibility) -> None:
        self.visibility = visibility

    def check(self) -> PermissionResult:
        if self.visibility != CommentVisibility.NOTE:
            return PermissionResult(False, "Required NOTE comment visibility")

        return PermissionResult(True)


class IsCommentAuthorRule:
    def __init__(self, subject: Subject, comment: Comment) -> None:
        self.subject = subject
        self.comment = comment

    def check(self) -> PermissionResult:
        if self.subject.id != self.comment.author_id:
            return PermissionResult(False, "You are not comment author")

        return PermissionResult(True)
