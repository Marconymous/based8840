"""App factory: builds the FastAPI app, its lifespan, routers and error handlers."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine

from app.api.dependencies import AppResources
from app.api.errors import register_error_handlers
from app.api.request_id import RequestIdMiddleware
from app.api.v1.router import OPENAPI_TAGS
from app.api.v1.router import router as v1_router
from app.core.log_setup import configure_logging
from app.core.settings import AppConfig
from app.storage.db.session import create_engine, create_session_factory


def create_app(config: AppConfig) -> FastAPI:
    configure_logging(level=config.settings.log_level, log_format=config.settings.log_format)
    engine: AsyncEngine = create_engine(config.settings.database)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        yield
        await engine.dispose()

    app = FastAPI(title=config.settings.app_name, lifespan=lifespan, openapi_tags=OPENAPI_TAGS)
    app.state.resources = AppResources(
        config=config, engine=engine, session_factory=create_session_factory(engine)
    )
    app.include_router(v1_router)
    app.add_middleware(RequestIdMiddleware)
    register_error_handlers(app, debug_errors=config.settings.debug_errors)
    return app
