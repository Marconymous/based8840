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
    # orderBy names fields in snake_case (AIP-132); enum members are their UPPER_SNAKE form.
    fields: dict[str, BookOrderField] = {field.value.lower(): field for field in BookOrderField}
    if name not in fields:
        supported: str = ", ".join(fields)
        raise InvalidArgumentError(f"Unsupported orderBy field {name!r}. Supported: {supported}.")
    return fields[name]
