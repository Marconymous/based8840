"""Test helpers."""

import textwrap
from pathlib import Path

from based8840.source import SourceModule, parse_source


def make_module(source: str, *, path: str) -> SourceModule:
    module: SourceModule | None = parse_source(path=Path(path), source=textwrap.dedent(source))
    assert module is not None
    return module
