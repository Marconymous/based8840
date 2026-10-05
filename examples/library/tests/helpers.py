"""Test helpers."""

from collections.abc import Sequence
from pathlib import Path
from typing import Final

from httpx import Response
from pydantic import TypeAdapter
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.settings import PROJECT_DIR
from app.models.api.v1.error import ErrorResponse

MIGRATIONS_DIR: Final = PROJECT_DIR / "migrations"
JSON_OBJECT: Final = TypeAdapter(dict[str, object])


def migration_statements(migrations_dir: Path) -> list[str]:
    """The Atlas migrations, split into single statements (aiosqlite runs one at a time)."""
    return [
        statement.strip()
        for path in sorted(migrations_dir.glob("*.sql"))
        for statement in path.read_text(encoding="utf-8").split(";\n")
        if statement.strip()
    ]


async def apply_migrations(*, engine: AsyncEngine, statements: Sequence[str]) -> None:
    async with engine.begin() as connection:
        for statement in statements:
            _ = await connection.exec_driver_sql(statement)


def json_object(response: Response) -> dict[str, object]:
    """Raw JSON body, to assert wire-level details such as camelCase keys."""
    return JSON_OBJECT.validate_json(response.content)


def error_status(response: Response) -> str:
    return ErrorResponse.model_validate_json(response.content).error.status
