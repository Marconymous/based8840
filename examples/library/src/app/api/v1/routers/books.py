"""HTTP routes for books: schema to domain, one service call, domain to schema."""

from typing import Annotated, Final
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query
from fastapi.responses import JSONResponse
from pydantic.main import IncEx

from app.api.dependencies import get_book_service, get_config
from app.api.field_mask import parse_field_mask, resolve_update_mask
from app.api.filtering import parse_book_filter
from app.api.ordering import parse_book_order_by
from app.api.pagination import next_page_token, page_request
from app.core.ids import RESOURCE_ID_PATTERN
from app.core.settings import AppConfig
from app.models.api.v1.book import (
    BookResponse,
    BorrowBookRequest,
    CreateBookRequest,
    ListBooksResponse,
    UpdateBookRequest,
)
from app.models.domain.book import Book, BookQuery
from app.models.domain.page import Page, PageRequest
from app.services.books import BookService

router = APIRouter(tags=["books"])

UPDATABLE_FIELDS: Final = frozenset({"title", "author", "description"})
READABLE_FIELDS: Final = frozenset(BookResponse.model_fields)


@router.get("/shelves/{shelf}/books/{book}")
async def get_book(
    shelf: Annotated[str, Path(pattern=RESOURCE_ID_PATTERN)],
    book: Annotated[str, Path(pattern=RESOURCE_ID_PATTERN)],
    service: Annotated[BookService, Depends(get_book_service)],
) -> BookResponse:
    found: Book = await service.get(shelf_id=shelf, book_id=book)
    return BookResponse.from_domain(found)


@router.get("/shelves/{shelf}/books", response_model=ListBooksResponse)
async def list_books(
    *,
    shelf: Annotated[str, Path(pattern=RESOURCE_ID_PATTERN)],
    service: Annotated[BookService, Depends(get_book_service)],
    config: Annotated[AppConfig, Depends(get_config)],
    page_size: Annotated[
        int | None, Query(alias="pageSize", description="Default 25, maximum 100.")
    ] = None,
    page_token: Annotated[str, Query(alias="pageToken")] = "",
    filter_: Annotated[
        str, Query(alias="filter", description='e.g. `state = "BORROWED" AND author = "X"`')
    ] = "",
    order_by: Annotated[
        str, Query(alias="orderBy", description="e.g. `create_time desc, title`")
    ] = "",
    show_deleted: Annotated[bool, Query(alias="showDeleted")] = False,
    read_mask: Annotated[
        str, Query(alias="readMask", description="e.g. `title,author`; `name` is always set.")
    ] = "",
) -> JSONResponse:
    # A page token is only valid for the query it was issued for (AIP-158).
    query_key = f"filter={filter_}&orderBy={order_by}&showDeleted={show_deleted}"
    page: PageRequest = page_request(
        page_size=page_size,
        page_token=page_token,
        query=query_key,
        settings=config.settings.pagination,
        secret=config.secrets.page_token_secret,
    )
    query = BookQuery(
        shelf_id=shelf,
        filter=parse_book_filter(filter_),
        order_by=parse_book_order_by(order_by),
        show_deleted=show_deleted,
        page=page,
    )
    result: Page[Book] = await service.list_books(query)
    response = ListBooksResponse(
        books=[BookResponse.from_domain(book) for book in result.items],
        next_page_token=next_page_token(
            page=page,
            has_more=result.has_more,
            query=query_key,
            secret=config.secrets.page_token_secret,
        ),
    )
    include: IncEx | None = _read_mask_include(read_mask)
    return JSONResponse(response.model_dump(mode="json", by_alias=True, include=include))


@router.post("/shelves/{shelf}/books")
async def create_book(
    *,
    shelf: Annotated[str, Path(pattern=RESOURCE_ID_PATTERN)],
    body: CreateBookRequest,
    service: Annotated[BookService, Depends(get_book_service)],
    book_id: Annotated[str | None, Query(alias="bookId", pattern=RESOURCE_ID_PATTERN)] = None,
    request_id: Annotated[
        UUID | None, Query(alias="requestId", description="Retries with the same ID are no-ops.")
    ] = None,
    validate_only: Annotated[bool, Query(alias="validateOnly")] = False,
) -> BookResponse:
    created: Book = await service.create(
        shelf_id=shelf,
        book_id=book_id,
        fields=body.to_domain(),
        request_id=None if request_id is None else str(request_id),
        validate_only=validate_only,
    )
    return BookResponse.from_domain(created)


@router.patch("/shelves/{shelf}/books/{book}")
async def update_book(
    *,
    shelf: Annotated[str, Path(pattern=RESOURCE_ID_PATTERN)],
    book: Annotated[str, Path(pattern=RESOURCE_ID_PATTERN)],
    body: UpdateBookRequest,
    service: Annotated[BookService, Depends(get_book_service)],
    update_mask: Annotated[
        str, Query(alias="updateMask", description="e.g. `title,author`, or `*`.")
    ] = "",
    etag: Annotated[str, Query(description="If set, must match the current etag.")] = "",
    validate_only: Annotated[bool, Query(alias="validateOnly")] = False,
) -> BookResponse:
    mask: frozenset[str] = resolve_update_mask(
        mask=update_mask, sent_fields=body.model_fields_set, allowed=UPDATABLE_FIELDS
    )
    updated: Book = await service.update(
        shelf_id=shelf,
        book_id=book,
        patch=body.to_domain(),
        update_mask=mask,
        etag=etag or None,
        validate_only=validate_only,
    )
    return BookResponse.from_domain(updated)


@router.delete("/shelves/{shelf}/books/{book}")
async def delete_book(
    shelf: Annotated[str, Path(pattern=RESOURCE_ID_PATTERN)],
    book: Annotated[str, Path(pattern=RESOURCE_ID_PATTERN)],
    service: Annotated[BookService, Depends(get_book_service)],
    etag: Annotated[str, Query(description="If set, must match the current etag.")] = "",
) -> BookResponse:
    """Soft delete (AIP-164): returns the book with `deleteTime` set."""
    deleted: Book = await service.delete(shelf_id=shelf, book_id=book, etag=etag or None)
    return BookResponse.from_domain(deleted)


@router.post("/shelves/{shelf}/books/{book}:undelete")
async def undelete_book(
    shelf: Annotated[str, Path(pattern=RESOURCE_ID_PATTERN)],
    book: Annotated[str, Path(pattern=RESOURCE_ID_PATTERN)],
    service: Annotated[BookService, Depends(get_book_service)],
) -> BookResponse:
    restored: Book = await service.undelete(shelf_id=shelf, book_id=book)
    return BookResponse.from_domain(restored)


@router.post("/shelves/{shelf}/books/{book}:borrow")
async def borrow_book(
    shelf: Annotated[str, Path(pattern=RESOURCE_ID_PATTERN)],
    book: Annotated[str, Path(pattern=RESOURCE_ID_PATTERN)],
    body: BorrowBookRequest,
    service: Annotated[BookService, Depends(get_book_service)],
) -> BookResponse:
    borrowed: Book = await service.borrow(shelf_id=shelf, book_id=book, borrower=body.borrower)
    return BookResponse.from_domain(borrowed)


@router.post("/shelves/{shelf}/books/{book}:return")
async def return_book(
    shelf: Annotated[str, Path(pattern=RESOURCE_ID_PATTERN)],
    book: Annotated[str, Path(pattern=RESOURCE_ID_PATTERN)],
    service: Annotated[BookService, Depends(get_book_service)],
) -> BookResponse:
    returned: Book = await service.return_book(shelf_id=shelf, book_id=book)
    return BookResponse.from_domain(returned)


def _read_mask_include(read_mask: str) -> IncEx | None:
    """readMask (AIP-157) -> pydantic `include`. `name` is always returned."""
    if not read_mask.strip():
        return None
    fields: frozenset[str] = parse_field_mask(mask=read_mask, allowed=READABLE_FIELDS)
    return {"books": {"__all__": {*fields, "name"}}, "next_page_token": True}
