from typing import Annotated, Final

from fastapi import APIRouter, BackgroundTasks, Depends, Path, Query

from app.api.background import run_export
from app.api.dependencies import (
    AppResources,
    get_config,
    get_operation_service,
    get_resources,
    get_shelf_service,
)
from app.api.field_mask import resolve_update_mask
from app.api.pagination import next_page_token, page_request
from app.core.ids import RESOURCE_ID_PATTERN
from app.core.settings import AppConfig
from app.models.api.v1.empty import Empty
from app.models.api.v1.operation import OperationResponse
from app.models.api.v1.shelf import (
    CreateShelfRequest,
    ListShelvesResponse,
    ShelfResponse,
    UpdateShelfRequest,
)
from app.models.domain.operation import Operation
from app.models.domain.page import Page, PageRequest
from app.models.domain.shelf import Shelf
from app.services.operations import OperationService
from app.services.shelves import ShelfService

router = APIRouter(tags=["shelves"])

UPDATABLE_FIELDS: Final = frozenset({"display_name", "genre"})


@router.get("/shelves/{shelf}")
async def get_shelf(
    shelf: Annotated[str, Path(pattern=RESOURCE_ID_PATTERN)],
    service: Annotated[ShelfService, Depends(get_shelf_service)],
) -> ShelfResponse:
    found: Shelf = await service.get(shelf)
    return ShelfResponse.from_domain(found)


@router.get("/shelves")
async def list_shelves(
    service: Annotated[ShelfService, Depends(get_shelf_service)],
    config: Annotated[AppConfig, Depends(get_config)],
    page_size: Annotated[
        int | None, Query(alias="pageSize", description="Default 25, maximum 100.")
    ] = None,
    page_token: Annotated[str, Query(alias="pageToken")] = "",
) -> ListShelvesResponse:
    page: PageRequest = page_request(
        page_size=page_size,
        page_token=page_token,
        query="",
        settings=config.settings.pagination,
        secret=config.secrets.page_token_secret,
    )
    result: Page[Shelf] = await service.list_shelves(page)
    return ListShelvesResponse(
        shelves=[ShelfResponse.from_domain(shelf) for shelf in result.items],
        next_page_token=next_page_token(
            page=page, has_more=result.has_more, query="", secret=config.secrets.page_token_secret
        ),
    )


@router.post("/shelves")
async def create_shelf(
    body: CreateShelfRequest,
    service: Annotated[ShelfService, Depends(get_shelf_service)],
    shelf_id: Annotated[str | None, Query(alias="shelfId", pattern=RESOURCE_ID_PATTERN)] = None,
) -> ShelfResponse:
    created: Shelf = await service.create(shelf_id=shelf_id, fields=body.to_domain())
    return ShelfResponse.from_domain(created)


@router.patch("/shelves/{shelf}")
async def update_shelf(
    shelf: Annotated[str, Path(pattern=RESOURCE_ID_PATTERN)],
    body: UpdateShelfRequest,
    service: Annotated[ShelfService, Depends(get_shelf_service)],
    update_mask: Annotated[
        str, Query(alias="updateMask", description="e.g. `display_name`, or `*`.")
    ] = "",
    etag: Annotated[str, Query(description="If set, must match the current etag.")] = "",
) -> ShelfResponse:
    mask: frozenset[str] = resolve_update_mask(
        mask=update_mask, sent_fields=body.model_fields_set, allowed=UPDATABLE_FIELDS
    )
    updated: Shelf = await service.update(
        shelf_id=shelf, patch=body.to_domain(), update_mask=mask, etag=etag or None
    )
    return ShelfResponse.from_domain(updated)


@router.delete("/shelves/{shelf}")
async def delete_shelf(
    shelf: Annotated[str, Path(pattern=RESOURCE_ID_PATTERN)],
    service: Annotated[ShelfService, Depends(get_shelf_service)],
    etag: Annotated[str, Query(description="If set, must match the current etag.")] = "",
) -> Empty:
    """Hard delete; fails with FAILED_PRECONDITION while the shelf holds books."""
    await service.delete(shelf_id=shelf, etag=etag or None)
    return Empty()


@router.post("/shelves/{shelf}:exportBooks")
async def export_books(
    shelf: Annotated[str, Path(pattern=RESOURCE_ID_PATTERN)],
    background_tasks: BackgroundTasks,
    service: Annotated[OperationService, Depends(get_operation_service)],
    resources: Annotated[AppResources, Depends(get_resources)],
) -> OperationResponse:
    """Starts a long-running export (AIP-151). Poll the returned operation."""
    operation: Operation = await service.start_export(shelf)
    background_tasks.add_task(run_export, resources=resources, operation_id=operation.operation_id)
    return OperationResponse.from_domain(operation)
