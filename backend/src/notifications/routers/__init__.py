__all__ = ["router"]

from fastapi import APIRouter

from .notifications import router as notification_router

router = APIRouter()

router.include_router(notification_router)
