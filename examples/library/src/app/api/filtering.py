"""Supported subset of the AIP-160 filter grammar for ListBooks.

    filter  = term { " AND " term }
    term    = field "=" '"' value '"'
    field   = "state" | "author"

Example: state = "BORROWED" AND author = "Ursula K. Le Guin"
Anything else is rejected with INVALID_ARGUMENT.
"""

import re
from typing import Final

from pydantic import BaseModel, ConfigDict

from app.core.errors import InvalidArgumentError
from app.models.domain.book import BookFilter, BookState

TERM_PATTERN: Final = re.compile(r'^\s*(?P<field>\w+)\s*=\s*"(?P<value>[^"]*)"\s*$')
FILTER_FIELDS: Final = frozenset({"state", "author"})


class FilterTerm(BaseModel):
    model_config = ConfigDict(frozen=True)

    field: str
    value: str


def parse_book_filter(text: str) -> BookFilter:
    if not text.strip():
        return BookFilter(state=None, author=None)
    terms: list[FilterTerm] = [_parse_term(raw) for raw in text.split(" AND ")]
    values: dict[str, str] = {term.field: term.value for term in terms}
    if len(values) != len(terms):
        raise InvalidArgumentError("Each filter field may appear only once.")
    state: str | None = values.get("state")
    return BookFilter(
        state=None if state is None else _parse_state(state),
        author=values.get("author"),
    )


def _parse_term(raw: str) -> FilterTerm:
    match: re.Match[str] | None = TERM_PATTERN.match(raw)
    if match is None:
        raise InvalidArgumentError(f'Unsupported filter term {raw!r}; expected field = "value".')
    term = FilterTerm(field=match["field"], value=match["value"])
    if term.field not in FILTER_FIELDS:
        supported: str = ", ".join(sorted(FILTER_FIELDS))
        raise InvalidArgumentError(
            f"Unsupported filter field {term.field!r}. Supported: {supported}."
        )
    return term


def _parse_state(value: str) -> BookState:
    try:
        return BookState(value)
    except ValueError as e:
        raise InvalidArgumentError(f"Unknown state {value!r}.") from e
