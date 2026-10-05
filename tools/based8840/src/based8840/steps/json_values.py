"""Typed access to JSON printed by ruff and basedpyright, narrowed with isinstance."""

import json
from collections.abc import Mapping


def load_json(text: str) -> object:
    """None when the tool printed something that is not JSON (e.g. it crashed)."""
    try:
        # json.loads is typed as returning Any; the result is narrowed by the helpers below.
        return json.loads(text)  # pyright: ignore[reportAny]
    except json.JSONDecodeError:
        return None


def as_mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, dict) else {}


def as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def as_str(value: object) -> str:
    return value if isinstance(value, str) else ""


def as_int(value: object) -> int:
    return value if isinstance(value, int) else 0
