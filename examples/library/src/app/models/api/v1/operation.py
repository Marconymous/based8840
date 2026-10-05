from datetime import datetime
from typing import Self

from pydantic import Field

from app.core.ids import operation_name, shelf_name
from app.models.api.v1.base import ApiModel
from app.models.api.v1.error import Status
from app.models.domain.operation import Operation


class ExportBooksMetadata(ApiModel):
    shelf: str
    create_time: datetime
    update_time: datetime


class ExportBooksResult(ApiModel):
    result_path: str = Field(description="Local path of the written JSON file.")
    exported_count: int


class OperationResponse(ApiModel):
    """Long-running operation (AIP-151). Poll GET /v1/operations/{operation} until done."""

    name: str = Field(description="OUTPUT_ONLY. `operations/{operation}`.")
    done: bool
    metadata: ExportBooksMetadata
    response: ExportBooksResult | None = Field(description="Set when done without error.")
    error: Status | None = Field(description="Set when done with an error.")

    @classmethod
    def from_domain(cls, operation: Operation) -> Self:
        return cls(
            name=operation_name(operation.operation_id),
            done=operation.done,
            metadata=ExportBooksMetadata(
                shelf=shelf_name(operation.shelf_id),
                create_time=operation.create_time,
                update_time=operation.update_time,
            ),
            response=_result(operation),
            error=_error(operation),
        )


def _result(operation: Operation) -> ExportBooksResult | None:
    if operation.result_path is None or operation.exported_count is None:
        return None
    return ExportBooksResult(
        result_path=operation.result_path, exported_count=operation.exported_count
    )


def _error(operation: Operation) -> Status | None:
    if operation.error_message is None:
        return None
    return Status(code=500, message=operation.error_message, status="INTERNAL", details=[])
