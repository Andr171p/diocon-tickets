from .domain.entities import Invitation, User
from .schemas import InvitationResponse, UserReference, UserResponse


def map_user_to_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        created_at=user.created_at,
        updated_at=user.updated_at,
        email=user.email.value,
        username=user.username.value if user.username else None,
        full_name=user.full_name.value if user.full_name else None,
        avatar_url=user.avatar_url,
        roles=user.roles,
        counterparty_id=user.counterparty_id,
        is_active=user.is_active,
    )


def map_user_to_reference(user: User) -> UserReference:
    return UserReference(
        id=user.id,
        full_name=user.full_name.value if user.full_name else None,
        email=user.email.value,
        type=user.type,
    )


def map_invitation_to_response(invitation: Invitation) -> InvitationResponse:
    return InvitationResponse(
        id=invitation.id,
        created_at=invitation.created_at,
        invited_by=invitation.invited_by,
        email=invitation.email.value,
        granted_roles=invitation.granted_roles,
        counterparty_id=invitation.counterparty_id,
        expires_at=invitation.expires_at,
        used_at=invitation.used_at,
        is_used=invitation.is_used,
    )
