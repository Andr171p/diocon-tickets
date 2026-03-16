import logging

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.core.errors import AppError
from src.routers import router

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Ticket management system",
    description="REST API тикет-системы компании 'ДИО-Консалт'",
    version="0.1.0"
)

app.include_router(router)


@app.exception_handler(AppError)
def app_exception_handler(request: Request, exc: AppError) -> JSONResponse:  # noqa: ARG001
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.status_code,
                "message": exc.public_message,
                "status": exc.status_code,
                "details": exc.details,
            }
        }
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host="0.0.0.0", port=8000)  # noqa: S104
