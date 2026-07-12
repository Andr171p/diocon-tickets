from fastapi import APIRouter

from .members import router as members_router
from .projects import router as projects_router
from .stages import router as stages_router

router = APIRouter()

router.include_router(members_router)
router.include_router(projects_router)
router.include_router(stages_router)
