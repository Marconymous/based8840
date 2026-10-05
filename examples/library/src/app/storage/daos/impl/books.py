"""SQL DAO for books."""

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import ColumnElement, UnaryExpression
from sqlalchemy.orm import Mapped
from sqlmodel import col, func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.domain.book import Book, BookOrder, BookOrderField, BookQuery, BookState
from app.models.domain.page import Page
from app.models.sql.book import BookRow
from app.storage.daos.base import to_page


class SqlBookDao:
    def __init__(self, session: AsyncSession) -> None:
        self._session: AsyncSession = session

    async def find(self, *, shelf_id: str, book_id: str) -> Book | None:
        row: BookRow | None = await self._session.get(BookRow, (shelf_id, book_id))
        return None if row is None else _to_domain(row)

    async def find_by_request_id(self, request_id: str) -> Book | None:
        statement = select(BookRow).where(col(BookRow.request_id) == request_id)
        row: BookRow | None = (await self._session.exec(statement)).first()
        return None if row is None else _to_domain(row)

    async def list_page(self, query: BookQuery) -> Page[Book]:
        statement = (
            select(BookRow)
            .where(*_conditions(query))
            .order_by(*[_order_clause(order) for order in query.order_by], col(BookRow.book_id))
            .offset(query.page.offset)
            .limit(query.page.limit + 1)
        )
        rows: Sequence[BookRow] = (await self._session.exec(statement)).all()
        return to_page(rows=[_to_domain(row) for row in rows], page=query.page)

    async def list_in_shelf(self, shelf_id: str) -> list[Book]:
        statement = (
            select(BookRow)
            .where(col(BookRow.shelf_id) == shelf_id, col(BookRow.delete_time).is_(None))
            .order_by(col(BookRow.book_id))
        )
        rows: Sequence[BookRow] = (await self._session.exec(statement)).all()
        return [_to_domain(row) for row in rows]

    async def list_due_before(self, due_before: datetime) -> list[Book]:
        statement = (
            select(BookRow)
            .where(
                col(BookRow.state) == BookState.BORROWED,
                col(BookRow.delete_time).is_(None),
                col(BookRow.due_time) < due_before,
            )
            .order_by(col(BookRow.due_time))
        )
        rows: Sequence[BookRow] = (await self._session.exec(statement)).all()
        return [_to_domain(row) for row in rows]

    async def count_in_shelf(self, shelf_id: str) -> int:
        statement = select(func.count()).where(col(BookRow.shelf_id) == shelf_id)
        count: int = (await self._session.exec(statement)).one()
        return count

    async def insert(self, book: Book) -> Book:
        self._session.add(_to_row(book))
        await self._session.flush()
        return book

    async def update(self, book: Book) -> Book:
        _ = await self._session.merge(_to_row(book))
        await self._session.flush()
        return book


def _conditions(query: BookQuery) -> list[ColumnElement[bool]]:
    optional: list[ColumnElement[bool] | None] = [
        None if query.show_deleted else col(BookRow.delete_time).is_(None),
        None if query.filter.state is None else col(BookRow.state) == query.filter.state,
        None if query.filter.author is None else col(BookRow.author) == query.filter.author,
    ]
    return [
        col(BookRow.shelf_id) == query.shelf_id,
        *[condition for condition in optional if condition is not None],
    ]


def _order_clause(order: BookOrder) -> UnaryExpression[str] | UnaryExpression[datetime]:
    columns: dict[BookOrderField, Mapped[str] | Mapped[datetime]] = {
        BookOrderField.CREATE_TIME: col(BookRow.create_time),
        BookOrderField.TITLE: col(BookRow.title),
        BookOrderField.AUTHOR: col(BookRow.author),
    }
    column: Mapped[str] | Mapped[datetime] = columns[order.field]
    return column.desc() if order.descending else column.asc()


def _to_domain(row: BookRow) -> Book:
    return Book.model_validate(row, from_attributes=True)


def _to_row(book: Book) -> BookRow:
    return BookRow(
        shelf_id=book.shelf_id,
        book_id=book.book_id,
        title=book.title,
        author=book.author,
        description=book.description,
        state=book.state,
        borrower=book.borrower,
        due_time=book.due_time,
        request_id=book.request_id,
        create_time=book.create_time,
        update_time=book.update_time,
        delete_time=book.delete_time,
        etag=book.etag,
    )
