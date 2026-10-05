"""Request-scoped values (AGENTS.md §4: the one allowed module-level state).

A ContextVar is copied per asyncio task, so concurrent requests never see each other's values.
"""

from contextvars import ContextVar
from typing import Final

NO_REQUEST_ID: Final = "-"
REQUEST_ID: Final[ContextVar[str]] = ContextVar("request_id", default=NO_REQUEST_ID)
