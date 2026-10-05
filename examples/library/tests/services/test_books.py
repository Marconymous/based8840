"""Service tests for books with a fake DAO."""

from datetime import UTC, datetime, timedelta
from typing import Final

import pytest

from app.core.errors import (
    AbortedError,
    AlreadyExistsError,
    FailedPreconditionError,
    InvalidArgumentError,
    NotFoundError,
)
from app.models.domain.book import Book, BookFields, BookPatch, BookState
from app.models.domain.shelf import Shelf
from app.services.books import BookService
from tests.fakes import FakeBookDao, FakeShelfDao

NOW: Final = datetime(2026, 1, 1, tzinfo=UTC)
FIELDS: Final = BookFields(title="Dune", author="Frank Herbert", description="")


@pytest.fixture
def book_dao() -> FakeBookDao:
    return FakeBookDao()


@pytest.fixture
def service(book_dao: FakeBookDao) -> BookService:
    shelf_dao = FakeShelfDao()
    shelf_dao.shelves["scifi"] = Shelf(
        shelf_id="scifi",
        display_name="Sci-Fi",
        genre="scifi",
        create_time=NOW,
        update_time=NOW,
        etag="e",
    )
    return BookService(dao=book_dao, shelf_dao=shelf_dao, loan_duration=timedelta(days=14))


async def create(service: BookService, *, book_id: str) -> Book:
    return await service.create(
        shelf_id="scifi", book_id=book_id, fields=FIELDS, request_id=None, validate_only=False
    )


async def test_create_in_missing_shelf_is_not_found(service: BookService) -> None:
    with pytest.raises(NotFoundError):
        _ = await service.create(
            shelf_id="nope", book_id="dune", fields=FIELDS, request_id=None, validate_only=False
        )


async def test_create_duplicate_id_already_exists(service: BookService) -> None:
    _ = await create(service, book_id="dune")

    with pytest.raises(AlreadyExistsError):
        _ = await create(service, book_id="dune")


async def test_create_with_same_request_id_returns_original(
    service: BookService, book_dao: FakeBookDao
) -> None:
    first: Book = await service.create(
        shelf_id="scifi", book_id=None, fields=FIELDS, request_id="r-1", validate_only=False
    )
    retry: Book = await service.create(
        shelf_id="scifi", book_id=None, fields=FIELDS, request_id="r-1", validate_only=False
    )

    assert retry == first
    assert len(book_dao.books) == 1


async def test_validate_only_does_not_persist(service: BookService, book_dao: FakeBookDao) -> None:
    book: Book = await service.create(
        shelf_id="scifi", book_id="dune", fields=FIELDS, request_id=None, validate_only=True
    )

    assert book.title == "Dune"
    assert book_dao.books == {}


async def test_update_applies_only_masked_fields(service: BookService) -> None:
    created: Book = await create(service, book_id="dune")

    updated: Book = await service.update(
        shelf_id="scifi",
        book_id="dune",
        patch=BookPatch(title="Dune Messiah", author="ignored", description=None),
        update_mask={"title"},
        etag=created.etag,
        validate_only=False,
    )

    assert updated.title == "Dune Messiah"
    assert updated.author == "Frank Herbert"
    assert updated.etag != created.etag


async def test_update_with_stale_etag_is_aborted(service: BookService) -> None:
    _ = await create(service, book_id="dune")

    with pytest.raises(AbortedError):
        _ = await service.update(
            shelf_id="scifi",
            book_id="dune",
            patch=BookPatch(title="x", author=None, description=None),
            update_mask={"title"},
            etag="stale",
            validate_only=False,
        )


async def test_update_mask_field_missing_from_body_is_invalid(service: BookService) -> None:
    _ = await create(service, book_id="dune")

    with pytest.raises(InvalidArgumentError, match="author"):
        _ = await service.update(
            shelf_id="scifi",
            book_id="dune",
            patch=BookPatch(title="x", author=None, description=None),
            update_mask={"title", "author"},
            etag=None,
            validate_only=False,
        )


async def test_borrow_sets_due_time_and_rejects_second_borrow(service: BookService) -> None:
    _ = await create(service, book_id="dune")

    borrowed: Book = await service.borrow(shelf_id="scifi", book_id="dune", borrower="paul@x")

    assert borrowed.state == BookState.BORROWED
    assert borrowed.due_time is not None
    assert borrowed.due_time - borrowed.update_time == timedelta(days=14)
    with pytest.raises(FailedPreconditionError):
        _ = await service.borrow(shelf_id="scifi", book_id="dune", borrower="other@x")


async def test_return_requires_borrowed_book(service: BookService) -> None:
    _ = await create(service, book_id="dune")

    with pytest.raises(FailedPreconditionError):
        _ = await service.return_book(shelf_id="scifi", book_id="dune")


async def test_soft_delete_and_undelete(service: BookService) -> None:
    created: Book = await create(service, book_id="dune")

    deleted: Book = await service.delete(shelf_id="scifi", book_id="dune", etag=created.etag)
    restored: Book = await service.undelete(shelf_id="scifi", book_id="dune")

    assert deleted.delete_time is not None
    assert restored.delete_time is None


async def test_deleted_book_cannot_be_borrowed(service: BookService) -> None:
    _ = await create(service, book_id="dune")
    _ = await service.delete(shelf_id="scifi", book_id="dune", etag=None)

    with pytest.raises(FailedPreconditionError, match="undelete"):
        _ = await service.borrow(shelf_id="scifi", book_id="dune", borrower="paul@x")
