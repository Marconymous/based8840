from pydantic import Field

from app.models.api.v1.base import ApiModel


class FieldViolation(ApiModel):
    field: str
    description: str


class Status(ApiModel):
    """AIP-193 error payload. Also used as `error` of a failed operation."""

    code: int = Field(description="HTTP status code, e.g. 404.")
    message: str = Field(description="Developer-facing, English.")
    status: str = Field(description="Canonical code, e.g. NOT_FOUND.")
    details: list[FieldViolation]


class ErrorResponse(ApiModel):
    error: Status
