"""ORM table for books."""

from datetime import datetime

from sqlmodel import Field, SQLModel

from app.models.domain.book import BookState
from app.models.sql.types import UtcDateTime


class BookRow(SQLModel, table=True):
    # SQLModel types __tablename__ as declared_attr; a plain string is what SQLAlchemy expects.
    __tablename__ = "books"  # pyright: ignore[reportAssignmentType]

    shelf_id: str = Field(foreign_key="shelves.shelf_id", primary_key=True, max_length=63)
    book_id: str = Field(primary_key=True, max_length=63)
    title: str
    author: str = Field(index=True)
    description: str
    state: BookState
    borrower: str | None
    due_time: datetime | None = Field(sa_type=UtcDateTime)
    request_id: str | None = Field(unique=True, max_length=36)
    create_time: datetime = Field(sa_type=UtcDateTime)
    update_time: datetime = Field(sa_type=UtcDateTime)
    delete_time: datetime | None = Field(sa_type=UtcDateTime)
    etag: str
