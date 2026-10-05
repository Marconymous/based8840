"""Applies an update mask to a partial model (AIP-134)."""

from collections.abc import Set

from pydantic import BaseModel

from app.core.errors import InvalidArgumentError


def masked_changes(*, patch: BaseModel, update_mask: Set[str]) -> dict[str, object]:
    """Values of the fields named in the update mask (AIP-134). Each must be present."""
    changes: dict[str, object] = patch.model_dump(include=set(update_mask))
    missing: list[str] = sorted(field for field, value in changes.items() if value is None)
    if missing:
        raise InvalidArgumentError(
            f"Fields in updateMask but missing from the body: {', '.join(missing)}."
        )
    return changes
