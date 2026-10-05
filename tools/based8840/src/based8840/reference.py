"""Locates the reference files (AGENTS.md, hooks, pyproject.toml) that `init` and drift use."""

import tomllib
from pathlib import Path
from typing import Final

# Installed wheel: bundled next to this file (see force-include in tools/based8840/pyproject.toml).
BUNDLED_DIR: Final = Path(__file__).parent / "reference"
# Editable install or `uv run --project tools/based8840`: the repo root of the based8840 repo.
REPO_ROOT: Final = Path(__file__).resolve().parents[4]


def reference_dir() -> Path:
    return BUNDLED_DIR if BUNDLED_DIR.is_dir() else REPO_ROOT


def load_reference_pyproject() -> dict[str, object]:
    pyproject: Path = reference_dir() / "pyproject.toml"
    return tomllib.loads(pyproject.read_text(encoding="utf-8"))
