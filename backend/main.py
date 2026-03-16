import logging

import uvicorn
from fastapi import FastAPI

from src.routers import router

app = FastAPI(
    title="Ticket management system",
    description="REST API тикет-системы компании 'ДИО-Консалт'",
    version="0.1.0"
)

app.include_router(router)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host="0.0.0.0", port=8000)  # noqa: S104
