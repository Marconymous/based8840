"""Tests for filter, orderBy and updateMask parsing."""

import pytest

from app.api.field_mask import parse_field_mask, resolve_update_mask
from app.api.filtering import parse_book_filter
from app.api.ordering import parse_book_order_by
from app.core.errors import InvalidArgumentError
from app.models.domain.book import BookFilter, BookOrder, BookOrderField, BookState


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("", BookFilter(state=None, author=None)),
        ('state = "BORROWED"', BookFilter(state=BookState.BORROWED, author=None)),
        (
            'state="AVAILABLE" AND author = "Le Guin"',
            BookFilter(state=BookState.AVAILABLE, author="Le Guin"),
        ),
    ],
)
def test_parse_book_filter(text: str, expected: BookFilter) -> None:
    assert parse_book_filter(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        'title = "x"',  # unsupported field
        "state = BORROWED",  # value not quoted
        'state = "LOST"',  # unknown enum value
        'author = "a" AND author = "b"',  # duplicate field
        'author = "a" OR state = "BORROWED"',  # OR is not supported
    ],
)
def test_parse_book_filter_rejects(text: str) -> None:
    with pytest.raises(InvalidArgumentError):
        _ = parse_book_filter(text)


def test_parse_order_by() -> None:
    assert parse_book_order_by("create_time desc, title") == [
        BookOrder(field=BookOrderField.CREATE_TIME, descending=True),
        BookOrder(field=BookOrderField.TITLE, descending=False),
    ]


@pytest.mark.parametrize("text", ["isbn", "title asc", "title desc extra"])
def test_parse_order_by_rejects(text: str) -> None:
    with pytest.raises(InvalidArgumentError):
        _ = parse_book_order_by(text)


def test_field_mask_star_means_all() -> None:
    assert parse_field_mask(mask="*", allowed={"a", "b"}) == {"a", "b"}


def test_field_mask_rejects_unknown_path() -> None:
    with pytest.raises(InvalidArgumentError, match="isbn"):
        _ = parse_field_mask(mask="title,isbn", allowed={"title"})


def test_empty_update_mask_uses_sent_fields() -> None:
    mask: frozenset[str] = resolve_update_mask(
        mask="", sent_fields={"title", "etag"}, allowed={"title", "author"}
    )

    assert mask == {"title"}
