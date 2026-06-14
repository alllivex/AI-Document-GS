from contextlib import asynccontextmanager

from fastapi import FastAPI
import uvicorn

from app.api.documents import router as documents_router
from app.api.health import router as health_router
from app.api.settings import router as settings_router
from app.api.tasks import router as tasks_router
from app.api.templates import router as templates_router
from app.api.trace import router as trace_router
from app.core.config import create_required_directories, get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings)
    create_required_directories(settings)
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="AI Document Generation System", version="0.1.0", lifespan=lifespan)
    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(settings_router)
    app.include_router(templates_router)
    app.include_router(tasks_router)
    app.include_router(documents_router)
    app.include_router(trace_router)
    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)
