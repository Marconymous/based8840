"""Tests for the opt-in layer rules."""

import pytest

from based8840.rules import layers
from tests.helpers import make_module


def codes(source: str, *, path: str) -> list[str]:
    return [finding.code for finding in layers.check(make_module(source, path=path), package="app")]


@pytest.mark.parametrize(
    ("path", "source", "expected"),
    [
        ("src/app/services/books.py", "from fastapi import HTTPException", ["BL001"]),
        ("src/app/services/books.py", "import sqlalchemy.orm", ["BL001"]),
        ("src/app/services/books.py", "from app.models import api", ["BL001"]),
        ("src/app/services/books.py", "from app.models.domain.book import Book", []),
        ("src/app/services/books.py", "async def f(s):\n    await s.commit()", ["BL002"]),
        ("src/app/storage/daos/impl/books.py", "from app.api.errors import x", ["BL001"]),
        ("src/app/storage/daos/impl/books.py", "from sqlmodel import select", []),
        ("src/app/api/v1/routers/books.py", "from app.storage.daos import base", ["BL001"]),
        ("src/app/api/dependencies.py", "from app.storage.daos import base", []),
        ("src/app/integrations/llm/base.py", "from app.services import books", ["BL001"]),
        ("src/app/models/domain/book.py", "from app.models.api.v1 import book", ["BL001"]),
        ("src/app/storage/db/session.py", "async def f(s):\n    await s.commit()", []),
        ("src/other/services/books.py", "import fastapi", []),
    ],
)
def test_layers_limit_imports_and_commits(path: str, source: str, expected: list[str]) -> None:
    assert codes(source, path=path) == expected
