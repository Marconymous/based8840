"""Locates the project to check and its package under `src/`."""

import tomllib
from pathlib import Path

from based8840.errors import PackageNotFoundError, ProjectNotFoundError


def find_project_dir(start: Path) -> Path:
    """Nearest directory, from `start` upwards, whose `pyproject.toml` has a `[project]` table."""
    candidates: list[Path] = [start, *start.parents]
    project_dir: Path | None = next((path for path in candidates if is_project(path)), None)
    if project_dir is None:
        raise ProjectNotFoundError(
            f"No pyproject.toml with a [project] table in {start} or its parents."
        )
    return project_dir


def detect_package(project_dir: Path) -> str:
    """Name of the single package under `src/` (a directory with `__init__.py`)."""
    src_dir: Path = project_dir / "src"
    packages: list[str] = (
        sorted(child.name for child in src_dir.iterdir() if (child / "__init__.py").is_file())
        if src_dir.is_dir()
        else []
    )
    if len(packages) != 1:
        found: str = ", ".join(packages) or "none"
        raise PackageNotFoundError(
            f"Layer checks need exactly one package under {src_dir}, found: {found}."
        )
    return packages[0]


def is_project(directory: Path) -> bool:
    pyproject: Path = directory / "pyproject.toml"
    if not pyproject.is_file():
        return False
    return "project" in tomllib.loads(pyproject.read_text(encoding="utf-8"))
