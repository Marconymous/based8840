from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.settings import DatabaseSettings


def create_engine(settings: DatabaseSettings) -> AsyncEngine:
    return create_async_engine(settings.url, echo=settings.echo)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@asynccontextmanager
async def session_scope(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    """One transaction: commit on success, roll back on any exception.

    The only place that commits. Used by the request dependency and by background tasks.
    """
    async with session_factory() as session:
        try:
            yield session
        except BaseException:
            await session.rollback()
            raise
        await session.commit()
