"""Shared pytest fixtures."""

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.settings import (
    CONFIG_DIR,
    AppConfig,
    DatabaseSettings,
    NotifierSettings,
    Settings,
    load_config,
)
from app.factory import create_app
from app.storage.db.session import create_engine, create_session_factory
from tests.helpers import MIGRATIONS_DIR, apply_migrations, migration_statements


@pytest.fixture
def config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AppConfig:
    """config/test.toml, with every file (database, exports, notifications) under tmp_path."""
    monkeypatch.setenv("PAGE_TOKEN_SECRET", "test-secret")
    loaded: AppConfig = load_config(config_dir=CONFIG_DIR, environ={"APP_ENV": "test"})
    settings: Settings = loaded.settings.model_copy(
        update={
            "database": DatabaseSettings(
                url=f"sqlite+aiosqlite:///{tmp_path / 'test.db'}", echo=False
            ),
            "library": loaded.settings.library.model_copy(
                update={"export_dir": tmp_path / "exports"}
            ),
            "notifier": NotifierSettings(kind="file", file_path=tmp_path / "notifications.jsonl"),
        }
    )
    return loaded.model_copy(update={"settings": settings})


@pytest.fixture
async def engine(config: AppConfig) -> AsyncIterator[AsyncEngine]:
    """Test database built from the real Atlas migrations, so tests catch schema drift."""
    test_engine: AsyncEngine = create_engine(config.settings.database)
    await apply_migrations(engine=test_engine, statements=migration_statements(MIGRATIONS_DIR))
    yield test_engine
    await test_engine.dispose()


@pytest.fixture
def session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return create_session_factory(engine)


@pytest.fixture
def app(config: AppConfig, engine: AsyncEngine) -> FastAPI:
    # `engine` is requested only so the migrations run before the app opens the database.
    return create_app(config)


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
