from datetime import datetime

from sqlmodel import Field, SQLModel

from app.models.sql.types import UtcDateTime


class ShelfRow(SQLModel, table=True):
    # SQLModel types __tablename__ as declared_attr; a plain string is what SQLAlchemy expects.
    __tablename__ = "shelves"  # pyright: ignore[reportAssignmentType]

    shelf_id: str = Field(primary_key=True, max_length=63)
    display_name: str
    genre: str
    create_time: datetime = Field(sa_type=UtcDateTime)
    update_time: datetime = Field(sa_type=UtcDateTime)
    etag: str
