"""Parsed Python source files that the AST rules inspect."""

import ast
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class SourceModule:
    """One parsed file. `path` is relative to the project directory."""

    path: Path
    source: str
    tree: ast.Module


def load_source_modules(project_dir: Path) -> list[SourceModule]:
    """Every parsable `.py` file under `src/`."""
    paths: list[Path] = sorted((project_dir / "src").rglob("*.py"))
    parsed: list[SourceModule | None] = [
        parse_source(path=path.relative_to(project_dir), source=path.read_text(encoding="utf-8"))
        for path in paths
    ]
    return [module for module in parsed if module is not None]


def parse_source(*, path: Path, source: str) -> SourceModule | None:
    """None for a file with a syntax error: ruff reports it with a location, the rules skip it."""
    try:
        tree: ast.Module = ast.parse(source, filename=str(path))
    except SyntaxError:
        return None
    return SourceModule(path=path, source=source, tree=tree)
