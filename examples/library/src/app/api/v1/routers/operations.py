from typing import Annotated

from fastapi import APIRouter, Depends, Path

from app.api.dependencies import get_operation_service
from app.core.ids import RESOURCE_ID_PATTERN
from app.models.api.v1.operation import OperationResponse
from app.models.domain.operation import Operation
from app.services.operations import OperationService

router = APIRouter(tags=["operations"])


@router.get("/operations/{operation}")
async def get_operation(
    operation: Annotated[str, Path(pattern=RESOURCE_ID_PATTERN)],
    service: Annotated[OperationService, Depends(get_operation_service)],
) -> OperationResponse:
    found: Operation = await service.get(operation)
    return OperationResponse.from_domain(found)
