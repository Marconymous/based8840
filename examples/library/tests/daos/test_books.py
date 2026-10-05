from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Final

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.domain.book import (
    Book,
    BookFilter,
    BookOrder,
    BookOrderField,
    BookQuery,
    BookState,
)
from app.models.domain.page import Page, PageRequest
from app.models.domain.shelf import Shelf
from app.storage.daos.impl.books import SqlBookDao
from app.storage.daos.impl.shelves import SqlShelfDao

NOW: Final = datetime(2026, 1, 1, tzinfo=UTC)


def make_book(*, book_id: str, title: str, state: BookState, minutes: int) -> Book:
    created: datetime = NOW + timedelta(minutes=minutes)
    return Book(
        shelf_id="scifi",
        book_id=book_id,
        title=title,
        author="Le Guin" if state == BookState.BORROWED else "Herbert",
        description="",
        state=state,
        borrower="reader@example.com" if state == BookState.BORROWED else None,
        due_time=created if state == BookState.BORROWED else None,
        request_id=f"req-{book_id}",
        create_time=created,
        update_time=created,
        delete_time=None,
        etag="e",
    )


def make_query(*, filter_: BookFilter, order_by: list[BookOrder], limit: int) -> BookQuery:
    return BookQuery(
        shelf_id="scifi",
        filter=filter_,
        order_by=order_by,
        show_deleted=False,
        page=PageRequest(offset=0, limit=limit),
    )


@pytest.fixture
async def dao(session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[SqlBookDao]:
    async with session_factory() as session:
        _ = await SqlShelfDao(session).insert(
            Shelf(
                shelf_id="scifi",
                display_name="Sci-Fi",
                genre="scifi",
                create_time=NOW,
                update_time=NOW,
                etag="e",
            )
        )
        book_dao = SqlBookDao(session)
        _ = await book_dao.insert(
            make_book(book_id="a", title="C", state=BookState.AVAILABLE, minutes=1)
        )
        _ = await book_dao.insert(
            make_book(book_id="b", title="A", state=BookState.BORROWED, minutes=2)
        )
        _ = await book_dao.insert(
            make_book(book_id="c", title="B", state=BookState.AVAILABLE, minutes=3)
        )
        yield book_dao


async def test_round_trip_keeps_timezone(dao: SqlBookDao) -> None:
    found: Book | None = await dao.find(shelf_id="scifi", book_id="b")

    assert found is not None
    assert found.create_time == NOW + timedelta(minutes=2)
    assert found.create_time.tzinfo is UTC


async def test_list_orders_and_pages(dao: SqlBookDao) -> None:
    query: BookQuery = make_query(
        filter_=BookFilter(state=None, author=None),
        order_by=[BookOrder(field=BookOrderField.TITLE, descending=False)],
        limit=2,
    )

    page: Page[Book] = await dao.list_page(query)

    assert [book.title for book in page.items] == ["A", "B"]
    assert page.has_more


async def test_list_filters(dao: SqlBookDao) -> None:
    query: BookQuery = make_query(
        filter_=BookFilter(state=BookState.AVAILABLE, author="Herbert"),
        order_by=[BookOrder(field=BookOrderField.CREATE_TIME, descending=True)],
        limit=10,
    )

    page: Page[Book] = await dao.list_page(query)

    assert [book.book_id for book in page.items] == ["c", "a"]
    assert not page.has_more


async def test_list_hides_deleted(dao: SqlBookDao) -> None:
    book: Book | None = await dao.find(shelf_id="scifi", book_id="a")
    assert book is not None
    _ = await dao.update(book.model_copy(update={"delete_time": NOW}))
    query: BookQuery = make_query(
        filter_=BookFilter(state=None, author=None), order_by=[], limit=10
    )

    page: Page[Book] = await dao.list_page(query)
    with_deleted: Page[Book] = await dao.list_page(query.model_copy(update={"show_deleted": True}))

    assert [book.book_id for book in page.items] == ["b", "c"]
    assert len(with_deleted.items) == 3


async def test_find_by_request_id(dao: SqlBookDao) -> None:
    found: Book | None = await dao.find_by_request_id("req-c")

    assert found is not None
    assert found.book_id == "c"


async def test_list_due_before(dao: SqlBookDao) -> None:
    overdue: list[Book] = await dao.list_due_before(NOW + timedelta(days=1))

    assert [book.book_id for book in overdue] == ["b"]
