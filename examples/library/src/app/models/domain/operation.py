from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class OperationKind(StrEnum):
    EXPORT_BOOKS = "EXPORT_BOOKS"


class Operation(BaseModel):
    """Long-running operation (AIP-151). Export results are flattened into optional fields."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    operation_id: str
    kind: OperationKind
    shelf_id: str
    done: bool
    result_path: str | None
    exported_count: int | None
    error_message: str | None
    create_time: datetime
    update_time: datetime


class ExportResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    result_path: str
    exported_count: int
