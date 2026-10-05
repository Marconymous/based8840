"""AIP-132 orderBy: comma-separated fields, each optionally followed by " desc"."""

from app.core.errors import InvalidArgumentError
from app.models.domain.book import BookOrder, BookOrderField


def parse_book_order_by(text: str) -> list[BookOrder]:
    """Empty means oldest first: `create_time`."""
    if not text.strip():
        return [BookOrder(field=BookOrderField.CREATE_TIME, descending=False)]
    return [_parse_order(part) for part in text.split(",")]


def _parse_order(part: str) -> BookOrder:
    match part.split():
        case [field_name]:
            return BookOrder(field=_parse_field(field_name), descending=False)
        case [field_name, "desc"]:
            return BookOrder(field=_parse_field(field_name), descending=True)
        case _:
            raise InvalidArgumentError(
                f'Invalid orderBy term {part.strip()!r}; use "field [desc]".'
            )


def _parse_field(name: str) -> BookOrderField:
    try:
        return BookOrderField(name)
    except ValueError as e:
        supported: str = ", ".join(field.value for field in BookOrderField)
        raise InvalidArgumentError(
            f"Unsupported orderBy field {name!r}. Supported: {supported}."
        ) from e
