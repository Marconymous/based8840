"""ORM table for long-running operations."""

from datetime import datetime

from sqlmodel import Field, SQLModel

from app.models.domain.operation import OperationKind
from app.models.sql.types import UtcDateTime


class OperationRow(SQLModel, table=True):
    # SQLModel types __tablename__ as declared_attr; a plain string is what SQLAlchemy expects.
    __tablename__ = "operations"  # pyright: ignore[reportAssignmentType]

    operation_id: str = Field(primary_key=True, max_length=63)
    kind: OperationKind
    shelf_id: str = Field(max_length=63)
    done: bool
    result_path: str | None
    exported_count: int | None
    error_message: str | None
    create_time: datetime = Field(sa_type=UtcDateTime)
    update_time: datetime = Field(sa_type=UtcDateTime)
