from typing import Any

from .domain.entities import Notification


def map_notification_to_dict(notification: Notification) -> dict[str, Any]:
    return {
        "id": notification.id,
        "title": notification.title,
        "message": notification.message,
        "type": notification.type,
        "read": notification.read,
        "data": notification.data,
    }
