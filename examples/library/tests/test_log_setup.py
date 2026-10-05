import logging
from collections.abc import Iterator
from typing import Final

import pytest
from pydantic import TypeAdapter

from app.core.log_setup import JsonFormatter, TextFormatter
from app.core.request_context import REQUEST_ID

LOG_LINE: Final = TypeAdapter(dict[str, str])


@pytest.fixture
def request_id() -> Iterator[str]:
    token = REQUEST_ID.set("req-1")
    yield "req-1"
    REQUEST_ID.reset(token)


def _record(message: str) -> logging.LogRecord:
    return logging.LogRecord(
        name="app.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=message,
        args=None,
        exc_info=None,
    )


def test_json_formatter_emits_one_json_object_with_request_id(request_id: str) -> None:
    line = JsonFormatter().format(_record("book created"))

    entry = LOG_LINE.validate_json(line)
    assert entry["request_id"] == request_id
    assert entry["level"] == "INFO"
    assert entry["message"] == "book created"
    assert "\n" not in line


def test_text_formatter_prefixes_request_id(request_id: str) -> None:
    line = TextFormatter("%(message)s").format(_record("book created"))

    assert line == f"[{request_id}] book created"


def test_formatters_outside_a_request_use_placeholder() -> None:
    entry = LOG_LINE.validate_json(JsonFormatter().format(_record("startup")))

    assert entry["request_id"] == "-"
