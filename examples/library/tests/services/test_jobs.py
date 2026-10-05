from datetime import UTC, datetime, timedelta
from typing import Final

import pytest

from app.core.errors import InvalidArgumentError
from app.models.domain.book import Book, BookState
from app.models.domain.job import JobFields, JobKind, JobRun
from app.services.jobs import JobService, overdue_reminder
from tests.fakes import FakeBookDao, FakeJobDao, FakeNotifier

NOW: Final = datetime(2026, 1, 1, tzinfo=UTC)


def borrowed_book(*, book_id: str, due_time: datetime) -> Book:
    return Book(
        shelf_id="scifi",
        book_id=book_id,
        title=f"Title {book_id}",
        author="Author",
        description="",
        state=BookState.BORROWED,
        borrower=f"{book_id}@example.com",
        due_time=due_time,
        request_id=None,
        create_time=NOW,
        update_time=NOW,
        delete_time=None,
        etag="e",
    )


@pytest.fixture
def notifier() -> FakeNotifier:
    return FakeNotifier()


@pytest.fixture
def book_dao() -> FakeBookDao:
    return FakeBookDao()


@pytest.fixture
def service(book_dao: FakeBookDao, notifier: FakeNotifier) -> JobService:
    return JobService(dao=FakeJobDao(), book_dao=book_dao, notifier=notifier)


async def test_run_notifies_only_overdue_borrowers(
    service: JobService, book_dao: FakeBookDao, notifier: FakeNotifier
) -> None:
    past = datetime.now(UTC) - timedelta(days=10)
    future = datetime.now(UTC) + timedelta(days=10)
    _ = await book_dao.insert(borrowed_book(book_id="late", due_time=past))
    _ = await book_dao.insert(borrowed_book(book_id="fine", due_time=future))
    _ = await service.create(
        job_id="reminders",
        fields=JobFields(display_name="Reminders", kind=JobKind.OVERDUE_REMINDER, grace_days=1),
    )

    run: JobRun = await service.run("reminders")

    assert run.notified_count == 1
    assert [sent.recipient for sent in notifier.sent] == ["late@example.com"]
    assert (await service.get("reminders")).last_run_time == run.run_time


async def test_create_rejects_unspecified_kind(service: JobService) -> None:
    fields = JobFields(display_name="x", kind=JobKind.JOB_KIND_UNSPECIFIED, grace_days=0)

    with pytest.raises(InvalidArgumentError):
        _ = await service.create(job_id=None, fields=fields)


def test_overdue_reminder_text() -> None:
    reminder = overdue_reminder(borrowed_book(book_id="late", due_time=NOW))

    assert reminder is not None
    assert reminder.recipient == "late@example.com"
    assert "shelves/scifi/books/late" in reminder.body
