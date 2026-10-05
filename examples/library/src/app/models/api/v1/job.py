"""v1 API schemas for jobs."""

from datetime import datetime
from typing import Self

from pydantic import Field

from app.core.ids import job_name
from app.models.api.v1.base import ApiModel
from app.models.domain.job import Job, JobFields, JobKind, JobRun


class JobResponse(ApiModel):
    name: str = Field(description="OUTPUT_ONLY. Resource name `jobs/{job}`.")
    display_name: str
    kind: JobKind
    grace_days: int
    last_run_time: datetime | None = Field(description="OUTPUT_ONLY.")
    create_time: datetime = Field(description="OUTPUT_ONLY.")
    update_time: datetime = Field(description="OUTPUT_ONLY.")
    etag: str = Field(description="OUTPUT_ONLY.")

    @classmethod
    def from_domain(cls, job: Job) -> Self:
        return cls(
            name=job_name(job.job_id),
            display_name=job.display_name,
            kind=job.kind,
            grace_days=job.grace_days,
            last_run_time=job.last_run_time,
            create_time=job.create_time,
            update_time=job.update_time,
            etag=job.etag,
        )


class CreateJobRequest(ApiModel):
    """Body of CreateJob. REQUIRED: displayName, kind, graceDays."""

    display_name: str = Field(min_length=1, description="REQUIRED.")
    kind: JobKind = Field(description="REQUIRED. JOB_KIND_UNSPECIFIED is rejected.")
    grace_days: int = Field(ge=0, description="REQUIRED. Days after due_time before reminding.")

    def to_domain(self) -> JobFields:
        return JobFields(display_name=self.display_name, kind=self.kind, grace_days=self.grace_days)


class ListJobsResponse(ApiModel):
    jobs: list[JobResponse]
    next_page_token: str = Field(description="Empty when there are no more pages.")


class RunJobResponse(ApiModel):
    job: str = Field(description="Resource name of the job that ran.")
    notified_count: int
    run_time: datetime

    @classmethod
    def from_domain(cls, run: JobRun) -> Self:
        return cls(
            job=job_name(run.job_id), notified_count=run.notified_count, run_time=run.run_time
        )
