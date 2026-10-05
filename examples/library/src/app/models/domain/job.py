from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class JobKind(StrEnum):
    JOB_KIND_UNSPECIFIED = "JOB_KIND_UNSPECIFIED"
    OVERDUE_REMINDER = "OVERDUE_REMINDER"


class Job(BaseModel):
    """Recurring, configurable work (AIP-152). Triggered by POST /v1/jobs/{job}:run."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    job_id: str
    display_name: str
    kind: JobKind
    grace_days: int
    last_run_time: datetime | None
    create_time: datetime
    update_time: datetime
    etag: str


class JobFields(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    display_name: str
    kind: JobKind
    grace_days: int


class JobRun(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    job_id: str
    notified_count: int
    run_time: datetime
