from collections.abc import Set
from datetime import datetime, timedelta

from app.core.clock import utc_now
from app.core.errors import AlreadyExistsError, FailedPreconditionError, NotFoundError
from app.core.ids import book_name, check_etag, new_etag, new_resource_id, shelf_name
from app.core.patch import masked_changes
from app.models.domain.book import Book, BookFields, BookPatch, BookQuery, BookState
from app.models.domain.page import Page
from app.storage.daos.base import BookDao, ShelfDao


class BookService:
    def __init__(self, *, dao: BookDao, shelf_dao: ShelfDao, loan_duration: timedelta) -> None:
        self._dao: BookDao = dao
        self._shelf_dao: ShelfDao = shelf_dao
        self._loan_duration: timedelta = loan_duration

    async def get(self, *, shelf_id: str, book_id: str) -> Book:
        """Also returns soft-deleted books; they carry a delete_time (AIP-164)."""
        book: Book | None = await self._dao.find(shelf_id=shelf_id, book_id=book_id)
        if book is None:
            raise NotFoundError(
                f"Book '{book_name(shelf_id=shelf_id, book_id=book_id)}' not found."
            )
        return book

    async def list_books(self, query: BookQuery) -> Page[Book]:
        await self._require_shelf(query.shelf_id)
        return await self._dao.list_page(query)

    async def list_for_export(self, shelf_id: str) -> list[Book]:
        return await self._dao.list_in_shelf(shelf_id)

    async def create(
        self,
        *,
        shelf_id: str,
        book_id: str | None,
        fields: BookFields,
        request_id: str | None,
        validate_only: bool,
    ) -> Book:
        # Idempotency (AIP-155): a retried request returns the book the first attempt created.
        previous: Book | None = (
            None if request_id is None else await self._dao.find_by_request_id(request_id)
        )
        if previous is not None:
            return previous
        await self._require_shelf(shelf_id)
        resolved_id: str = book_id or new_resource_id(prefix="book")
        if await self._dao.find(shelf_id=shelf_id, book_id=resolved_id) is not None:
            name: str = book_name(shelf_id=shelf_id, book_id=resolved_id)
            raise AlreadyExistsError(f"Book '{name}' already exists.")
        now: datetime = utc_now()
        book = Book(
            shelf_id=shelf_id,
            book_id=resolved_id,
            title=fields.title,
            author=fields.author,
            description=fields.description,
            state=BookState.AVAILABLE,
            borrower=None,
            due_time=None,
            request_id=request_id,
            create_time=now,
            update_time=now,
            delete_time=None,
            etag=new_etag(),
        )
        if validate_only:
            return book
        return await self._dao.insert(book)

    async def update(
        self,
        *,
        shelf_id: str,
        book_id: str,
        patch: BookPatch,
        update_mask: Set[str],
        etag: str | None,
        validate_only: bool,
    ) -> Book:
        current: Book = await self._get_active(shelf_id=shelf_id, book_id=book_id, etag=etag)
        changes: dict[str, object] = masked_changes(patch=patch, update_mask=update_mask)
        updated: Book = current.model_copy(
            update={**changes, "update_time": utc_now(), "etag": new_etag()}
        )
        if validate_only:
            return updated
        return await self._dao.update(updated)

    async def delete(self, *, shelf_id: str, book_id: str, etag: str | None) -> Book:
        """Soft delete (AIP-164): the book stays in the database with a delete_time."""
        current: Book = await self._get_active(shelf_id=shelf_id, book_id=book_id, etag=etag)
        now: datetime = utc_now()
        deleted: Book = current.model_copy(
            update={"delete_time": now, "update_time": now, "etag": new_etag()}
        )
        return await self._dao.update(deleted)

    async def undelete(self, *, shelf_id: str, book_id: str) -> Book:
        current: Book = await self.get(shelf_id=shelf_id, book_id=book_id)
        if current.delete_time is None:
            name: str = book_name(shelf_id=shelf_id, book_id=book_id)
            raise FailedPreconditionError(f"Book '{name}' is not deleted.")
        restored: Book = current.model_copy(
            update={"delete_time": None, "update_time": utc_now(), "etag": new_etag()}
        )
        return await self._dao.update(restored)

    async def borrow(self, *, shelf_id: str, book_id: str, borrower: str) -> Book:
        current: Book = await self._get_active(shelf_id=shelf_id, book_id=book_id, etag=None)
        if current.state == BookState.BORROWED:
            name: str = book_name(shelf_id=shelf_id, book_id=book_id)
            raise FailedPreconditionError(f"Book '{name}' is already borrowed.")
        now: datetime = utc_now()
        borrowed: Book = current.model_copy(
            update={
                "state": BookState.BORROWED,
                "borrower": borrower,
                "due_time": now + self._loan_duration,
                "update_time": now,
                "etag": new_etag(),
            }
        )
        return await self._dao.update(borrowed)

    async def return_book(self, *, shelf_id: str, book_id: str) -> Book:
        current: Book = await self._get_active(shelf_id=shelf_id, book_id=book_id, etag=None)
        if current.state != BookState.BORROWED:
            name: str = book_name(shelf_id=shelf_id, book_id=book_id)
            raise FailedPreconditionError(f"Book '{name}' is not borrowed.")
        returned: Book = current.model_copy(
            update={
                "state": BookState.AVAILABLE,
                "borrower": None,
                "due_time": None,
                "update_time": utc_now(),
                "etag": new_etag(),
            }
        )
        return await self._dao.update(returned)

    async def _get_active(self, *, shelf_id: str, book_id: str, etag: str | None) -> Book:
        book: Book = await self.get(shelf_id=shelf_id, book_id=book_id)
        name: str = book_name(shelf_id=shelf_id, book_id=book_id)
        if book.delete_time is not None:
            raise FailedPreconditionError(f"Book '{name}' is deleted; undelete it first.")
        check_etag(expected=etag, actual=book.etag, resource_name=name)
        return book

    async def _require_shelf(self, shelf_id: str) -> None:
        if await self._shelf_dao.find(shelf_id) is None:
            raise NotFoundError(f"Shelf '{shelf_name(shelf_id)}' not found.")
