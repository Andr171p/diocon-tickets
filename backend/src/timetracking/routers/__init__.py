__all__ = ["router"]

from fastapi import APIRouter

from .timesheets import router as timesheets_router
from .worklogs import router as worklogs_router

router = APIRouter()  # noqa: RUF067

router.include_router(timesheets_router)  # noqa: RUF067
router.include_router(worklogs_router)  # noqa: RUF067
