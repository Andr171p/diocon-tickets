from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, status

from ..dependencies import CurrentUser, get_current_user, get_notification_service
from ..schemas import InvitationCreate
from ..services import NotificationService

router = APIRouter(prefix="/invitations", tags=["Приглашения"])


@router.post(
    path="",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Отправка приглашения"
)
async def send_invitation(
        current_user: Annotated[CurrentUser, Depends(get_current_user)],
        data: InvitationCreate,
        background_tasks: BackgroundTasks,
        service: NotificationService = Depends(get_notification_service),
) -> dict[str, str]:
    background_tasks.add_task(
        service.send_invitation,
        invited_by=current_user.user_id,
        email=data.email,
        intended_role=data.role,
        counterparty_id=data.counterparty_id,
    )
    return {"message": "Приглашение будет отправлено в ближайшее время"}
