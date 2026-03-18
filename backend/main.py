import logging
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from src.core.errors import AppError
from src.db.base import create_tables
from src.routers import router
from src.settings import settings
from src.utils.commons import run_cli_command

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    await create_tables()
    await run_cli_command(sys.executable, "-m", "cli", "create-first-admin")
    await run_cli_command(sys.executable, "-m", "cli", "init-s3-storage")
    yield


app = FastAPI(
    title="Ticket management system",
    description="REST API тикет-системы компании **ДИО-Консалт**",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(router)


@app.exception_handler(ValueError)
def value_exception_handler(request: Request, exc: ValueError) -> JSONResponse:  # noqa: ARG001
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": str(exc),
                "status": status.HTTP_400_BAD_REQUEST,
                "details": {},
            }
        }
    )


@app.exception_handler(AppError)
def app_exception_handler(request: Request, exc: AppError) -> JSONResponse:  # noqa: ARG001
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.public_message,
                "status": exc.status_code,
                "details": exc.details,
            }
        }
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host="0.0.0.0", port=settings.app.port)  # noqa: S104
