"""Field masks (AIP-157 readMask, AIP-134/161 updateMask). Paths are snake_case field names."""

from collections.abc import Set

from app.core.errors import InvalidArgumentError


def parse_field_mask(*, mask: str, allowed: Set[str]) -> frozenset[str]:
    """`"title,author"` -> {"title", "author"}; `"*"` -> every allowed field."""
    if mask.strip() == "*":
        return frozenset(allowed)
    paths: frozenset[str] = frozenset(path.strip() for path in mask.split(",") if path.strip())
    unknown: list[str] = sorted(paths - allowed)
    if unknown:
        supported: str = ", ".join(sorted(allowed))
        raise InvalidArgumentError(
            f"Unsupported field mask path(s): {', '.join(unknown)}. Supported: {supported}."
        )
    return paths


def resolve_update_mask(*, mask: str, sent_fields: Set[str], allowed: Set[str]) -> frozenset[str]:
    """An empty updateMask means "every field present in the body" (AIP-134)."""
    if mask.strip():
        return parse_field_mask(mask=mask, allowed=allowed)
    return frozenset(sent_fields) & frozenset(allowed)
