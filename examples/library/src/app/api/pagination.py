"""Opaque, tamper-proof page tokens (AIP-158).

A token is base64url(JSON cursor) + "." + base64url(HMAC-SHA256). Clients cannot edit the
offset, and a token is only valid for the same query (filter, orderBy, ...) it was issued for.
"""

import base64
import hashlib
import hmac

from pydantic import BaseModel, ConfigDict, SecretStr, ValidationError

from app.core.errors import InvalidArgumentError
from app.core.settings import PaginationSettings
from app.models.domain.page import PageRequest


class PageCursor(BaseModel):
    model_config = ConfigDict(frozen=True)

    offset: int
    query: str


def resolve_page_size(*, requested: int | None, settings: PaginationSettings) -> int:
    """0 or missing means the default; values above the maximum are coerced down."""
    if requested is None or requested == 0:
        return settings.default_page_size
    if requested < 0:
        raise InvalidArgumentError("pageSize must not be negative.")
    return min(requested, settings.max_page_size)


def page_request(
    *,
    page_size: int | None,
    page_token: str,
    query: str,
    settings: PaginationSettings,
    secret: SecretStr,
) -> PageRequest:
    offset: int = decode_page_token(token=page_token, query=query, secret=secret)
    return PageRequest(
        offset=offset, limit=resolve_page_size(requested=page_size, settings=settings)
    )


def next_page_token(*, page: PageRequest, has_more: bool, query: str, secret: SecretStr) -> str:
    if not has_more:
        return ""
    cursor = PageCursor(offset=page.offset + page.limit, query=query)
    return encode_page_token(cursor=cursor, secret=secret)


def encode_page_token(*, cursor: PageCursor, secret: SecretStr) -> str:
    payload: bytes = cursor.model_dump_json().encode()
    return f"{_b64encode(payload)}.{_b64encode(_sign(payload=payload, secret=secret))}"


def decode_page_token(*, token: str, query: str, secret: SecretStr) -> int:
    """Returns the offset; an empty token means the first page."""
    if not token:
        return 0
    payload_part, _, signature_part = token.partition(".")
    payload: bytes = _b64decode(payload_part)
    if not hmac.compare_digest(_b64decode(signature_part), _sign(payload=payload, secret=secret)):
        raise InvalidArgumentError("Invalid pageToken.")
    cursor: PageCursor = _parse_cursor(payload)
    if cursor.query != query:
        raise InvalidArgumentError("pageToken was issued for a different query.")
    return cursor.offset


def _parse_cursor(payload: bytes) -> PageCursor:
    try:
        return PageCursor.model_validate_json(payload)
    except ValidationError as e:
        raise InvalidArgumentError("Invalid pageToken.") from e


def _sign(*, payload: bytes, secret: SecretStr) -> bytes:
    return hmac.new(secret.get_secret_value().encode(), payload, hashlib.sha256).digest()


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _b64decode(text: str) -> bytes:
    try:
        return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))
    except ValueError as e:
        raise InvalidArgumentError("Invalid pageToken.") from e
