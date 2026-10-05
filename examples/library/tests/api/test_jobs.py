"""API tests for jobs."""

import asyncio
from pathlib import Path

from httpx import AsyncClient

from app.core.settings import AppConfig
from app.models.api.v1.job import JobResponse, RunJobResponse
from app.models.domain.notification import Notification
from tests.helpers import error_status


async def test_run_overdue_reminder_job(client: AsyncClient, config: AppConfig) -> None:
    # config/test.toml sets loan_days = 0, so a borrowed book is overdue right away.
    _ = await client.post(
        "/v1/shelves", params={"shelfId": "scifi"}, json={"displayName": "SF", "genre": "sf"}
    )
    _ = await client.post(
        "/v1/shelves/scifi/books",
        params={"bookId": "dune"},
        json={"title": "Dune", "author": "Herbert", "description": ""},
    )
    _ = await client.post("/v1/shelves/scifi/books/dune:borrow", json={"borrower": "paul@x"})
    created = await client.post(
        "/v1/jobs",
        params={"jobId": "reminders"},
        json={"displayName": "Reminders", "kind": "OVERDUE_REMINDER", "graceDays": 0},
    )

    run = RunJobResponse.model_validate_json((await client.post("/v1/jobs/reminders:run")).content)
    job = JobResponse.model_validate_json((await client.get("/v1/jobs/reminders")).content)

    assert JobResponse.model_validate_json(created.content).last_run_time is None
    assert run.job == "jobs/reminders"
    assert run.notified_count == 1
    assert job.last_run_time == run.run_time
    # The file notifier (selected in conftest) wrote one JSON line per reminder.
    lines: str = await asyncio.to_thread(Path(config.settings.notifier.file_path).read_text)
    sent: Notification = Notification.model_validate_json(lines.splitlines()[0])
    assert sent.recipient == "paul@x"


async def test_unspecified_job_kind_is_invalid_argument(client: AsyncClient) -> None:
    response = await client.post(
        "/v1/jobs", json={"displayName": "x", "kind": "JOB_KIND_UNSPECIFIED", "graceDays": 0}
    )

    assert response.status_code == 400
    assert error_status(response) == "INVALID_ARGUMENT"
