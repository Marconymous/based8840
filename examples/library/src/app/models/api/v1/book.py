from datetime import datetime
from typing import Self

from pydantic import Field

from app.core.ids import book_name
from app.models.api.v1.base import ApiModel
from app.models.domain.book import Book, BookFields, BookPatch, BookState


class BookResponse(ApiModel):
    name: str = Field(description="OUTPUT_ONLY. Resource name `shelves/{shelf}/books/{book}`.")
    title: str
    author: str
    description: str
    state: BookState = Field(description="OUTPUT_ONLY. Changed by :borrow and :return.")
    borrower: str | None = Field(description="OUTPUT_ONLY. Set while BORROWED.")
    due_time: datetime | None = Field(description="OUTPUT_ONLY. Set while BORROWED.")
    create_time: datetime = Field(description="OUTPUT_ONLY.")
    update_time: datetime = Field(description="OUTPUT_ONLY.")
    delete_time: datetime | None = Field(description="OUTPUT_ONLY. Set when soft-deleted.")
    etag: str = Field(description="OUTPUT_ONLY. Send back on update/delete (AIP-154).")

    @classmethod
    def from_domain(cls, book: Book) -> Self:
        return cls(
            name=book_name(shelf_id=book.shelf_id, book_id=book.book_id),
            title=book.title,
            author=book.author,
            description=book.description,
            state=book.state,
            borrower=book.borrower,
            due_time=book.due_time,
            create_time=book.create_time,
            update_time=book.update_time,
            delete_time=book.delete_time,
            etag=book.etag,
        )


class CreateBookRequest(ApiModel):
    """Body of CreateBook. REQUIRED: title, author, description (may be empty)."""

    title: str = Field(min_length=1, description="REQUIRED.")
    author: str = Field(min_length=1, description="REQUIRED.")
    description: str = Field(description="REQUIRED, may be empty.")

    def to_domain(self) -> BookFields:
        return BookFields(title=self.title, author=self.author, description=self.description)


class UpdateBookRequest(ApiModel):
    """Body of UpdateBook. Only fields named in `updateMask` are applied."""

    title: str | None = Field(default=None, min_length=1)
    author: str | None = Field(default=None, min_length=1)
    description: str | None = None

    def to_domain(self) -> BookPatch:
        return BookPatch(title=self.title, author=self.author, description=self.description)


class BorrowBookRequest(ApiModel):
    """Body of :borrow. REQUIRED: borrower (e-mail address used for reminders)."""

    borrower: str = Field(min_length=1, description="REQUIRED.")


class ListBooksResponse(ApiModel):
    books: list[BookResponse]
    next_page_token: str = Field(description="Empty when there are no more pages.")
