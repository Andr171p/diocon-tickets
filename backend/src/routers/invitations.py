from typing import Annotated

from fastapi import APIRouter, Depends, status

from ..dependencies import CurrentUser, get_current_user, get_notification_service
from ..schemas import InvitationCreate, InvitationResponse
from ..services.notification import NotificationService

router = APIRouter(prefix="/invitations", tags=["Приглашения"])


@router.post(
    path="",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=InvitationResponse,
    summary="Отправка приглашения"
)
async def send_invitation(
        current_user: Annotated[CurrentUser, Depends(get_current_user)],
        data: InvitationCreate,
        service: NotificationService = Depends(get_notification_service),
) -> InvitationResponse:
    invitation = await service.send_invitation(
        invited_by=current_user.user_id,
        email=data.email,
        intended_role=data.role,
        counterparty_id=data.counterparty_id,
    )
    return InvitationResponse.model_validate(invitation)
