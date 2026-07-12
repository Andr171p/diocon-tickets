from .entities import Comment


def remove_comment(comment: Comment, parent: Comment | None) -> None:
    """Удаление комментария с уменьшением счётчика ответов."""

    comment.remove()

    if parent:
        parent.decrement_reply_count()
