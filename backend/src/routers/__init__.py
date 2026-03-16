__all__ = ["router"]

from fastapi import APIRouter

from .auth import router as auth_router
from .counterparties import router as counterparties_router
from .invitations import router as invitation_router
from .users import router as users_router

router = APIRouter(prefix="/api/v1")

router.include_router(auth_router)
router.include_router(counterparties_router)
router.include_router(invitation_router)
router.include_router(users_router)
