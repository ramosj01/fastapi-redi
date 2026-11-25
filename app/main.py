from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.container import Container
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.presentation.api.error_handlers import register_error_handlers
from app.presentation.api.middleware.request_context import RequestContextMiddleware
from app.presentation.api.v1.router import api_router, health_router


def create_app(settings: Settings | None = None, container: Container | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level, settings.instance_id)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.container = container or Container(settings)
        try:
            yield
        finally:
            await app.state.container.shutdown()

    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
    app.add_middleware(RequestContextMiddleware, instance_id=settings.instance_id)
    register_error_handlers(app)
    app.include_router(health_router)
    app.include_router(api_router)
    return app


app = create_app()
