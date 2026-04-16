from enum import StrEnum


class NotificationType(StrEnum):
    """Типы уведомлений в системе"""

    TICKET_CREATED = "ticket_created"
    TICKET_ASSIGNED = "ticket_assigned"
    TICKET_STATUS_CHANGED = "ticket_status_changed"
    COMMENT_ADDED = "comment_added"
    SYSTEM = "system"
