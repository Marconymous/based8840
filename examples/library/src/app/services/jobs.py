"""Business logic for jobs."""

import logging
from datetime import datetime, timedelta
from typing import Final

from app.core.clock import utc_now
from app.core.errors import AlreadyExistsError, InvalidArgumentError, NotFoundError
from app.core.ids import book_name, job_name, new_etag, new_resource_id
from app.integrations.notifier.base import Notifier
from app.models.domain.book import Book
from app.models.domain.job import Job, JobFields, JobKind, JobRun
from app.models.domain.notification import Notification
from app.models.domain.page import Page, PageRequest
from app.storage.daos.base import BookDao, JobDao

logger: Final = logging.getLogger(__name__)


class JobService:
    def __init__(self, *, dao: JobDao, book_dao: BookDao, notifier: Notifier) -> None:
        self._dao: JobDao = dao
        self._book_dao: BookDao = book_dao
        self._notifier: Notifier = notifier

    async def get(self, job_id: str) -> Job:
        job: Job | None = await self._dao.find(job_id)
        if job is None:
            raise NotFoundError(f"Job '{job_name(job_id)}' not found.")
        return job

    async def list_jobs(self, page: PageRequest) -> Page[Job]:
        return await self._dao.list_page(page)

    async def create(self, *, job_id: str | None, fields: JobFields) -> Job:
        if fields.kind == JobKind.JOB_KIND_UNSPECIFIED:
            raise InvalidArgumentError("kind must be set.")
        resolved_id: str = job_id or new_resource_id(prefix="job")
        if await self._dao.find(resolved_id) is not None:
            raise AlreadyExistsError(f"Job '{job_name(resolved_id)}' already exists.")
        now: datetime = utc_now()
        job = Job(
            job_id=resolved_id,
            display_name=fields.display_name,
            kind=fields.kind,
            grace_days=fields.grace_days,
            last_run_time=None,
            create_time=now,
            update_time=now,
            etag=new_etag(),
        )
        return await self._dao.insert(job)

    async def run(self, job_id: str) -> JobRun:
        """Sends one reminder per overdue book. The flow is visible here, step by step."""
        job: Job = await self.get(job_id)
        now: datetime = utc_now()
        overdue: list[Book] = await self._book_dao.list_due_before(
            now - timedelta(days=job.grace_days)
        )
        reminders: list[Notification] = [
            reminder for book in overdue if (reminder := overdue_reminder(book)) is not None
        ]
        for reminder in reminders:
            await self._notifier.send(reminder)
        _ = await self._dao.update(
            job.model_copy(update={"last_run_time": now, "update_time": now, "etag": new_etag()})
        )
        logger.info("job %s sent %d reminder(s)", job_name(job_id), len(reminders))
        return JobRun(job_id=job_id, notified_count=len(reminders), run_time=now)


def overdue_reminder(book: Book) -> Notification | None:
    if book.borrower is None or book.due_time is None:
        return None
    return Notification(
        recipient=book.borrower,
        subject=f"Overdue: {book.title}",
        body=(
            f"'{book.title}' ({book_name(shelf_id=book.shelf_id, book_id=book.book_id)}) "
            f"was due on {book.due_time.isoformat()}. Please return it."
        ),
    )
