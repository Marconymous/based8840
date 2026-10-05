"""Tests for `based8840 init`: copying the agent files and merging the tool config."""

import os
import textwrap
import tomllib
from pathlib import Path

import pytest
from rich.console import Console

from based8840.errors import InitConflictError, ProjectNotFoundError
from based8840.init import init_project
from tests.helpers import dig

TARGET_PYPROJECT = textwrap.dedent(
    """\
    [project]
    name = "shop"
    version = "0.1.0"

    # kept as written
    [tool.ruff]
    line-length = 120

    [tool.ruff.lint]
    select = ["E", "F"]
    """
)


@pytest.fixture
def project(tmp_path: Path) -> Path:
    _ = (tmp_path / "pyproject.toml").write_text(TARGET_PYPROJECT)
    (tmp_path / "src" / "shop").mkdir(parents=True)
    (tmp_path / "src" / "shop" / "__init__.py").touch()
    return tmp_path


def run_init(project: Path, *, is_forced: bool) -> str:
    console = Console(record=True, width=200)
    assert init_project(project, is_forced=is_forced, console=console) == 0
    return console.export_text()


def test_init_copies_agent_files_and_links_copilot(project: Path) -> None:
    _ = run_init(project, is_forced=False)
    assert (project / "AGENTS.md").read_text().startswith("# AGENTS.md")
    assert (project / "CLAUDE.md").is_file()
    assert (project / ".claude" / "settings.json").is_file()
    link = project / ".github" / "copilot-instructions.md"
    assert link.is_symlink()
    assert link.readlink() == Path("../AGENTS.md")
    hook = project / ".claude" / "hooks" / "py-postedit.sh"
    assert os.access(hook, os.X_OK)


def test_init_merges_tool_config(project: Path) -> None:
    output = run_init(project, is_forced=False)
    text = (project / "pyproject.toml").read_text()
    merged: dict[str, object] = tomllib.loads(text)
    select = dig(merged, "tool", "ruff", "lint", "select")
    assert isinstance(select, list)
    assert select[:3] == ["E", "F", "W"]
    assert "FAST" in select
    assert dig(merged, "tool", "ruff", "line-length") == 120
    assert dig(merged, "tool", "ruff", "lint", "mccabe", "max-complexity") == 10
    assert dig(merged, "tool", "basedpyright", "reportAny") == "error"
    assert "# kept as written" in text
    assert "kept tool.ruff.line-length = 120 (reference: 100)" in output
    assert "uv add --dev ruff basedpyright" in output


def test_init_renames_the_reference_package(project: Path) -> None:
    _ = run_init(project, is_forced=False)
    merged: dict[str, object] = tomllib.loads((project / "pyproject.toml").read_text())
    per_file = dig(merged, "tool", "ruff", "lint", "per-file-ignores")
    banned = dig(merged, "tool", "ruff", "lint", "flake8-tidy-imports", "banned-api")
    assert isinstance(per_file, dict)
    assert isinstance(banned, dict)
    assert "src/shop/storage/**" in per_file
    assert "shop.models.sql" in banned


def test_init_aborts_without_writing_when_files_exist(project: Path) -> None:
    _ = (project / "CLAUDE.md").write_text("mine")
    with pytest.raises(InitConflictError, match=r"CLAUDE\.md"):
        _ = run_init(project, is_forced=False)
    assert not (project / "AGENTS.md").exists()
    assert (project / "pyproject.toml").read_text() == TARGET_PYPROJECT


def test_init_force_overwrites(project: Path) -> None:
    _ = (project / "CLAUDE.md").write_text("mine")
    _ = run_init(project, is_forced=True)
    assert (project / "CLAUDE.md").read_text() != "mine"


def test_init_twice_with_force_merges_nothing_new(project: Path) -> None:
    _ = run_init(project, is_forced=False)
    first = (project / "pyproject.toml").read_text()
    _ = run_init(project, is_forced=True)
    assert (project / "pyproject.toml").read_text() == first


def test_init_needs_a_project(tmp_path: Path) -> None:
    with pytest.raises(ProjectNotFoundError):
        _ = run_init(tmp_path, is_forced=False)
