"""Resource IDs, resource names (AIP-122) and etags (AIP-154)."""

from typing import Final
from uuid import uuid4

from app.core.errors import AbortedError

RESOURCE_ID_PATTERN: Final = r"^[a-z][a-z0-9-]{0,62}$"


def new_resource_id(*, prefix: str) -> str:
    """Server-generated ID, used when the client does not pick one (AIP-133)."""
    return f"{prefix}-{uuid4().hex[:12]}"


def new_etag() -> str:
    return uuid4().hex


def check_etag(*, expected: str | None, actual: str, resource_name: str) -> None:
    """An empty/missing etag skips the check; a stale one aborts (AIP-154)."""
    if expected and expected != actual:
        raise AbortedError(f"Etag mismatch for '{resource_name}': the resource was modified.")


def shelf_name(shelf_id: str) -> str:
    return f"shelves/{shelf_id}"


def book_name(*, shelf_id: str, book_id: str) -> str:
    return f"shelves/{shelf_id}/books/{book_id}"


def operation_name(operation_id: str) -> str:
    return f"operations/{operation_id}"


def job_name(job_id: str) -> str:
    return f"jobs/{job_id}"
