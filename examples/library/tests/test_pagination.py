"""Tests for page token encoding and decoding."""

from typing import Final

import pytest
from pydantic import SecretStr

from app.api.pagination import (
    PageCursor,
    decode_page_token,
    encode_page_token,
    resolve_page_size,
)
from app.core.errors import InvalidArgumentError
from app.core.settings import PaginationSettings

SECRET: Final = SecretStr("secret")
SETTINGS: Final = PaginationSettings(default_page_size=25, max_page_size=100)


def test_token_round_trip() -> None:
    token: str = encode_page_token(cursor=PageCursor(offset=50, query="q"), secret=SECRET)

    assert decode_page_token(token=token, query="q", secret=SECRET) == 50


def test_empty_token_is_first_page() -> None:
    assert decode_page_token(token="", query="q", secret=SECRET) == 0


def test_token_is_opaque() -> None:
    token: str = encode_page_token(cursor=PageCursor(offset=50, query="q"), secret=SECRET)

    assert "50" not in token.split(".")[1]
    assert "offset" not in token


@pytest.mark.parametrize(
    "token",
    ["garbage", "e30.e30", "not base64!.x"],
)
def test_malformed_token_is_rejected(token: str) -> None:
    with pytest.raises(InvalidArgumentError):
        _ = decode_page_token(token=token, query="q", secret=SECRET)


def test_token_signed_with_other_secret_is_rejected() -> None:
    token: str = encode_page_token(
        cursor=PageCursor(offset=50, query="q"), secret=SecretStr("other")
    )

    with pytest.raises(InvalidArgumentError, match="Invalid pageToken"):
        _ = decode_page_token(token=token, query="q", secret=SECRET)


def test_token_for_other_query_is_rejected() -> None:
    token: str = encode_page_token(cursor=PageCursor(offset=50, query="a"), secret=SECRET)

    with pytest.raises(InvalidArgumentError, match="different query"):
        _ = decode_page_token(token=token, query="b", secret=SECRET)


@pytest.mark.parametrize(
    ("requested", "expected"),
    [(None, 25), (0, 25), (10, 10), (100, 100), (1000, 100)],
)
def test_resolve_page_size(requested: int | None, expected: int) -> None:
    assert resolve_page_size(requested=requested, settings=SETTINGS) == expected


def test_negative_page_size_is_rejected() -> None:
    with pytest.raises(InvalidArgumentError):
        _ = resolve_page_size(requested=-1, settings=SETTINGS)
