from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from app.api.dependencies import get_config, get_job_service
from app.api.pagination import next_page_token, page_request
from app.core.ids import RESOURCE_ID_PATTERN
from app.core.settings import AppConfig
from app.models.api.v1.job import CreateJobRequest, JobResponse, ListJobsResponse, RunJobResponse
from app.models.domain.job import Job, JobRun
from app.models.domain.page import Page, PageRequest
from app.services.jobs import JobService

router = APIRouter(tags=["jobs"])


@router.get("/jobs/{job}")
async def get_job(
    job: Annotated[str, Path(pattern=RESOURCE_ID_PATTERN)],
    service: Annotated[JobService, Depends(get_job_service)],
) -> JobResponse:
    found: Job = await service.get(job)
    return JobResponse.from_domain(found)


@router.get("/jobs")
async def list_jobs(
    service: Annotated[JobService, Depends(get_job_service)],
    config: Annotated[AppConfig, Depends(get_config)],
    page_size: Annotated[
        int | None, Query(alias="pageSize", description="Default 25, maximum 100.")
    ] = None,
    page_token: Annotated[str, Query(alias="pageToken")] = "",
) -> ListJobsResponse:
    page: PageRequest = page_request(
        page_size=page_size,
        page_token=page_token,
        query="",
        settings=config.settings.pagination,
        secret=config.secrets.page_token_secret,
    )
    result: Page[Job] = await service.list_jobs(page)
    return ListJobsResponse(
        jobs=[JobResponse.from_domain(job) for job in result.items],
        next_page_token=next_page_token(
            page=page, has_more=result.has_more, query="", secret=config.secrets.page_token_secret
        ),
    )


@router.post("/jobs")
async def create_job(
    body: CreateJobRequest,
    service: Annotated[JobService, Depends(get_job_service)],
    job_id: Annotated[str | None, Query(alias="jobId", pattern=RESOURCE_ID_PATTERN)] = None,
) -> JobResponse:
    created: Job = await service.create(job_id=job_id, fields=body.to_domain())
    return JobResponse.from_domain(created)


@router.post("/jobs/{job}:run")
async def run_job(
    job: Annotated[str, Path(pattern=RESOURCE_ID_PATTERN)],
    service: Annotated[JobService, Depends(get_job_service)],
) -> RunJobResponse:
    """Runs the job now and waits for it (it is quick: one reminder per overdue book)."""
    run: JobRun = await service.run(job)
    return RunJobResponse.from_domain(run)
