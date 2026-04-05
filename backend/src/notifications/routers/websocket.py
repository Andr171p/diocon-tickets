from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from ...iam.dependencies import get_current_user_ws
from ...iam.schemas import CurrentUser
from ...shared.dependencies import ws_manager

router = APIRouter(prefix="/ws", tags=["Websocket"])


@router.websocket("/notifications")
async def websocket_notifications(
        websocket: WebSocket, current_user: CurrentUser = Depends(get_current_user_ws)
):
    if current_user is None:
        return
    await ws_manager.connect(websocket, current_user.user_id)
    try:
        data = await websocket.receive_json()
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket, current_user.user_id)
