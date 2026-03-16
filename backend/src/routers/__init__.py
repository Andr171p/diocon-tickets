__all__ = ["router"]

from fastapi import APIRouter

from .counterparties import router as counterparties_router

router = APIRouter(prefix="/api/v1")

router.include_router(counterparties_router)
