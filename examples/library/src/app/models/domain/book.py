"""Domain models for books."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from app.models.domain.page import PageRequest


class BookState(StrEnum):
    STATE_UNSPECIFIED = "STATE_UNSPECIFIED"
    AVAILABLE = "AVAILABLE"
    BORROWED = "BORROWED"


class Book(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    shelf_id: str
    book_id: str
    title: str
    author: str
    description: str
    state: BookState
    borrower: str | None
    due_time: datetime | None
    request_id: str | None
    create_time: datetime
    update_time: datetime
    delete_time: datetime | None
    etag: str


class BookFields(BaseModel):
    """Client-writable fields of a book (create body, update body)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    title: str
    author: str
    description: str


class BookOrderField(StrEnum):
    CREATE_TIME = "CREATE_TIME"
    TITLE = "TITLE"
    AUTHOR = "AUTHOR"


class BookOrder(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    field: BookOrderField
    descending: bool


class BookFilter(BaseModel):
    """Parsed form of the supported AIP-160 subset; None means "no condition"."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    state: BookState | None
    author: str | None


class BookQuery(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    shelf_id: str
    filter: BookFilter
    order_by: list[BookOrder]
    show_deleted: bool
    page: PageRequest


class BookPatch(BaseModel):
    """Update input; None means "not sent". Only fields in the update mask are applied."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    title: str | None
    author: str | None
    description: str | None
