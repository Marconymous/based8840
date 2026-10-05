"""Test helpers."""

import textwrap
from pathlib import Path

from based8840.source import SourceModule, parse_source


def make_module(source: str, *, path: str) -> SourceModule:
    module: SourceModule | None = parse_source(path=Path(path), source=textwrap.dedent(source))
    assert module is not None
    return module


def dig(value: object, *keys: str | int) -> object:
    """Nested lookup in parsed JSON / TOML without `Any`: a missing key gives None."""
    if not keys:
        return value
    key, *rest = keys
    if isinstance(key, int):
        child: object = value[key] if isinstance(value, list) and key < len(value) else None
    else:
        child = value.get(key) if isinstance(value, dict) else None
    return dig(child, *rest)
