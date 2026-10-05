"""FastAPI dependency chain: request -> resources -> session -> DAOs -> services.

Routes write `Annotated[XService, Depends(get_x_service)]` inline; there are no aliases.
"""

from collections.abc import AsyncIterator
from datetime import timedelta
from typing import Annotated

from fastapi import Depends, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.settings import AppConfig
from app.integrations.notifier.base import Notifier
from app.integrations.notifier.factory import create_notifier
from app.services.books import BookService
from app.services.jobs import JobService
from app.services.operations import OperationService
from app.services.shelves import ShelfService
from app.storage.daos.base import BookDao, JobDao, OperationDao, ShelfDao
from app.storage.daos.impl.books import SqlBookDao
from app.storage.daos.impl.jobs import SqlJobDao
from app.storage.daos.impl.operations import SqlOperationDao
from app.storage.daos.impl.shelves import SqlShelfDao
from app.storage.db.session import session_scope


class AppResources(BaseModel):
    """Everything built once at startup (see app/factory.py)."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    config: AppConfig
    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]


async def get_resources(request: Request) -> AppResources:
    # Starlette types `app.state` as Any, so this one line cannot be typed. factory.create_app
    # stores AppResources there; the isinstance check turns it back into a typed value.
    resources: object = request.app.state.resources  # pyright: ignore[reportAny]
    if not isinstance(resources, AppResources):
        raise TypeError("app.state.resources is not set; build the app with create_app().")
    return resources


async def get_config(resources: Annotated[AppResources, Depends(get_resources)]) -> AppConfig:
    return resources.config


async def get_session(
    resources: Annotated[AppResources, Depends(get_resources)],
) -> AsyncIterator[AsyncSession]:
    """Request-scoped transaction: commits if the route succeeds, rolls back if it raises.

    Used with `scope="function"` so the commit happens before the response is sent.
    """
    async with session_scope(resources.session_factory) as session:
        yield session


async def get_shelf_dao(
    session: Annotated[AsyncSession, Depends(get_session, scope="function")],
) -> ShelfDao:
    return SqlShelfDao(session)


async def get_book_dao(
    session: Annotated[AsyncSession, Depends(get_session, scope="function")],
) -> BookDao:
    return SqlBookDao(session)


async def get_operation_dao(
    session: Annotated[AsyncSession, Depends(get_session, scope="function")],
) -> OperationDao:
    return SqlOperationDao(session)


async def get_job_dao(
    session: Annotated[AsyncSession, Depends(get_session, scope="function")],
) -> JobDao:
    return SqlJobDao(session)


async def get_notifier(config: Annotated[AppConfig, Depends(get_config)]) -> Notifier:
    return create_notifier(config.settings.notifier)


async def get_shelf_service(
    dao: Annotated[ShelfDao, Depends(get_shelf_dao)],
    book_dao: Annotated[BookDao, Depends(get_book_dao)],
) -> ShelfService:
    return ShelfService(dao=dao, book_dao=book_dao)


async def get_book_service(
    dao: Annotated[BookDao, Depends(get_book_dao)],
    shelf_dao: Annotated[ShelfDao, Depends(get_shelf_dao)],
    config: Annotated[AppConfig, Depends(get_config)],
) -> BookService:
    loan_duration = timedelta(days=config.settings.library.loan_days)
    return BookService(dao=dao, shelf_dao=shelf_dao, loan_duration=loan_duration)


async def get_operation_service(
    dao: Annotated[OperationDao, Depends(get_operation_dao)],
    shelf_dao: Annotated[ShelfDao, Depends(get_shelf_dao)],
    config: Annotated[AppConfig, Depends(get_config)],
) -> OperationService:
    return OperationService(
        dao=dao, shelf_dao=shelf_dao, export_dir=config.settings.library.export_dir
    )


async def get_job_service(
    dao: Annotated[JobDao, Depends(get_job_dao)],
    book_dao: Annotated[BookDao, Depends(get_book_dao)],
    notifier: Annotated[Notifier, Depends(get_notifier)],
) -> JobService:
    return JobService(dao=dao, book_dao=book_dao, notifier=notifier)
