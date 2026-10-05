from collections.abc import Sequence

from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.domain.job import Job
from app.models.domain.page import Page, PageRequest
from app.models.sql.job import JobRow
from app.storage.daos.base import to_page


class SqlJobDao:
    def __init__(self, session: AsyncSession) -> None:
        self._session: AsyncSession = session

    async def find(self, job_id: str) -> Job | None:
        row: JobRow | None = await self._session.get(JobRow, job_id)
        return None if row is None else Job.model_validate(row, from_attributes=True)

    async def list_page(self, page: PageRequest) -> Page[Job]:
        statement = (
            select(JobRow)
            .order_by(col(JobRow.create_time), col(JobRow.job_id))
            .offset(page.offset)
            .limit(page.limit + 1)
        )
        rows: Sequence[JobRow] = (await self._session.exec(statement)).all()
        jobs: list[Job] = [Job.model_validate(row, from_attributes=True) for row in rows]
        return to_page(rows=jobs, page=page)

    async def insert(self, job: Job) -> Job:
        self._session.add(_to_row(job))
        await self._session.flush()
        return job

    async def update(self, job: Job) -> Job:
        _ = await self._session.merge(_to_row(job))
        await self._session.flush()
        return job


def _to_row(job: Job) -> JobRow:
    return JobRow(
        job_id=job.job_id,
        display_name=job.display_name,
        kind=job.kind,
        grace_days=job.grace_days,
        last_run_time=job.last_run_time,
        create_time=job.create_time,
        update_time=job.update_time,
        etag=job.etag,
    )
