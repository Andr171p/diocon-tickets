from fastapi import APIRouter

from .comments import router as comments_router
from .crud import router as crud_router
from .workflow import router as workflow_router

router = APIRouter()

router.include_router(comments_router)
router.include_router(crud_router)
router.include_router(workflow_router)

__all__ = ["router"]
