from fastapi import APIRouter, Depends, status

from ..dependencies import get_notification_service
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
        data: InvitationCreate,
        service: NotificationService = Depends(get_notification_service),
): ...
