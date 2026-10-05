"""Current time as a timezone-aware UTC datetime."""

from datetime import UTC, datetime


def utc_now() -> datetime:
    return datetime.now(UTC)
