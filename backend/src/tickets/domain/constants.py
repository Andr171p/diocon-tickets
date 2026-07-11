from .vo import CommentType

# Человеко-читаемые типы комментариев (для UI)
COMMENT_TYPE_DISPLAY_NAMES: dict[CommentType, str] = {
    CommentType.INTERNAL: "Внутренний",
    CommentType.PUBLIC: "Публичный",
    CommentType.NOTE: "Личный (заметка)"
}
