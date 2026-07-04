from dataclasses import dataclass
from uuid import UUID

from src.shared.domain.events import Event

from .vo import Email, UserRole


@dataclass(frozen=True, kw_only=True)
class UserInvited(Event):
    """
    Пользователю отправлено приглашение.
    """

    invitation_id: UUID
    email: Email
    granted_roles: set[UserRole]
    counterparty_id: UUID | None = None
    invited_by: UUID
