"""Logging setup (AGENTS.md §7): text or JSON lines, each carrying the request ID."""

import json
import logging
from datetime import UTC, datetime
from typing import Final, Literal, override

from app.core.request_context import REQUEST_ID

TEXT_FORMAT: Final = "%(asctime)s %(levelname)s %(name)s %(message)s"


class TextFormatter(logging.Formatter):
    @override
    def format(self, record: logging.LogRecord) -> str:
        return f"[{REQUEST_ID.get()}] {super().format(record)}"


class JsonFormatter(logging.Formatter):
    """One JSON object per line, for log collectors in prod."""

    @override
    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, str] = {
            "time": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "request_id": REQUEST_ID.get(),
            "message": record.getMessage(),
        }
        exception: dict[str, str] = (
            {"exception": self.formatException(record.exc_info)} if record.exc_info else {}
        )
        return json.dumps(entry | exception)


def create_formatter(log_format: Literal["json", "text"]) -> logging.Formatter:
    if log_format == "json":
        return JsonFormatter()
    return TextFormatter(TEXT_FORMAT)


def configure_logging(*, level: str, log_format: Literal["json", "text"]) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(create_formatter(log_format))
    logging.basicConfig(level=level, handlers=[handler])
