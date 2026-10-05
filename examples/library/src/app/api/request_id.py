"""X-Request-Id middleware: every request gets an ID that log lines and the response carry."""

import re
from typing import Final, override
from uuid import uuid4

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.request_context import REQUEST_ID

REQUEST_ID_HEADER: Final = "X-Request-Id"
# Client IDs are echoed into logs, so only a safe charset is accepted (no log injection).
CLIENT_REQUEST_ID_PATTERN: Final = re.compile(r"^[A-Za-z0-9._-]{1,128}$")


def resolve_request_id(header_value: str | None) -> str:
    if header_value and CLIENT_REQUEST_ID_PATTERN.fullmatch(header_value):
        return header_value
    return uuid4().hex


class RequestIdMiddleware(BaseHTTPMiddleware):
    @override
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id: str = resolve_request_id(request.headers.get(REQUEST_ID_HEADER))
        # Not reset afterwards: the 500 handler runs outside this middleware (in Starlette's
        # ServerErrorMiddleware) and must still log the ID. Each request runs in its own task,
        # so the value does not outlive it.
        _ = REQUEST_ID.set(request_id)
        response: Response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response
