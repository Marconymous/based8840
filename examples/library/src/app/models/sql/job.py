from datetime import datetime

from sqlmodel import Field, SQLModel

from app.models.domain.job import JobKind
from app.models.sql.types import UtcDateTime


class JobRow(SQLModel, table=True):
    # SQLModel types __tablename__ as declared_attr; a plain string is what SQLAlchemy expects.
    __tablename__ = "jobs"  # pyright: ignore[reportAssignmentType]

    job_id: str = Field(primary_key=True, max_length=63)
    display_name: str
    kind: JobKind
    grace_days: int
    last_run_time: datetime | None = Field(sa_type=UtcDateTime)
    create_time: datetime = Field(sa_type=UtcDateTime)
    update_time: datetime = Field(sa_type=UtcDateTime)
    etag: str
