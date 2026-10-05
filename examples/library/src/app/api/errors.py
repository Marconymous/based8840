"""The single place that turns exceptions into AIP-193 error responses.

Routes never build error responses: they let domain exceptions propagate to here.
"""

import logging
from collections.abc import Mapping, Sequence
from typing import Final

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from starlette.exceptions import HTTPException

from app.core.errors import (
    AbortedError,
    AlreadyExistsError,
    FailedPreconditionError,
    InvalidArgumentError,
    LibraryError,
    NotFoundError,
)
from app.models.api.v1.error import ErrorResponse, FieldViolation, Status

logger: Final = logging.getLogger(__name__)


class CanonicalCode(BaseModel):
    model_config = ConfigDict(frozen=True)

    http_code: int
    status: str


INVALID_ARGUMENT: Final = CanonicalCode(http_code=400, status="INVALID_ARGUMENT")
INTERNAL: Final = CanonicalCode(http_code=500, status="INTERNAL")

CODE_BY_ERROR: Final[Mapping[type[LibraryError], CanonicalCode]] = {
    InvalidArgumentError: INVALID_ARGUMENT,
    FailedPreconditionError: CanonicalCode(http_code=400, status="FAILED_PRECONDITION"),
    NotFoundError: CanonicalCode(http_code=404, status="NOT_FOUND"),
    AlreadyExistsError: CanonicalCode(http_code=409, status="ALREADY_EXISTS"),
    AbortedError: CanonicalCode(http_code=409, status="ABORTED"),
}

CODE_BY_HTTP_STATUS: Final[Mapping[int, CanonicalCode]] = {
    404: CanonicalCode(http_code=404, status="NOT_FOUND"),
    405: CanonicalCode(http_code=405, status="UNIMPLEMENTED"),
}


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(LibraryError, handle_library_error)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(HTTPException, handle_http_exception)
    app.add_exception_handler(Exception, handle_unexpected_error)


async def handle_library_error(_request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, LibraryError):
        return await handle_unexpected_error(_request, exc)
    code: CanonicalCode = CODE_BY_ERROR.get(type(exc), INTERNAL)
    return error_response(code=code, message=str(exc), details=[])


async def handle_validation_error(_request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, RequestValidationError):
        return await handle_unexpected_error(_request, exc)
    errors: Sequence[Mapping[str, object]] = exc.errors()
    violations: list[FieldViolation] = [_field_violation(error) for error in errors]
    return error_response(
        code=INVALID_ARGUMENT, message="Request validation failed.", details=violations
    )


async def handle_http_exception(_request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, HTTPException):
        return await handle_unexpected_error(_request, exc)
    code: CanonicalCode = CODE_BY_HTTP_STATUS.get(
        exc.status_code, CanonicalCode(http_code=exc.status_code, status="UNKNOWN")
    )
    return error_response(code=code, message=exc.detail, details=[])


async def handle_unexpected_error(_request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error", exc_info=exc)
    return error_response(code=INTERNAL, message="Internal error.", details=[])


def error_response(
    *, code: CanonicalCode, message: str, details: Sequence[FieldViolation]
) -> JSONResponse:
    body = ErrorResponse(
        error=Status(
            code=code.http_code, message=message, status=code.status, details=list(details)
        )
    )
    return JSONResponse(status_code=code.http_code, content=body.model_dump(by_alias=True))


def _field_violation(error: Mapping[str, object]) -> FieldViolation:
    location: object = error.get("loc", ())
    parts: list[str] = (
        [str(part) for part in location] if isinstance(location, list | tuple) else []
    )
    return FieldViolation(field=".".join(parts), description=str(error.get("msg", "")))
