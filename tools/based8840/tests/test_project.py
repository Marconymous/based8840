"""Tests for project and package discovery."""

from pathlib import Path

import pytest

from based8840.errors import PackageNotFoundError, ProjectNotFoundError
from based8840.project import detect_package, find_project_dir


def write_pyproject(directory: Path, content: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    _ = (directory / "pyproject.toml").write_text(content)


def test_find_project_dir_walks_up_to_a_project(tmp_path: Path) -> None:
    write_pyproject(tmp_path, '[project]\nname = "demo"\n')
    nested: Path = tmp_path / "src" / "app"
    nested.mkdir(parents=True)
    assert find_project_dir(nested) == tmp_path


def test_find_project_dir_skips_pyproject_without_project_table(tmp_path: Path) -> None:
    write_pyproject(tmp_path, '[project]\nname = "outer"\n')
    write_pyproject(tmp_path / "tools", "[tool.ruff]\nline-length = 100\n")
    assert find_project_dir(tmp_path / "tools") == tmp_path


def test_find_project_dir_fails_without_project(tmp_path: Path) -> None:
    with pytest.raises(ProjectNotFoundError):
        _ = find_project_dir(tmp_path)


def test_detect_package_finds_the_single_package(tmp_path: Path) -> None:
    (tmp_path / "src" / "app").mkdir(parents=True)
    _ = (tmp_path / "src" / "app" / "__init__.py").write_text("")
    (tmp_path / "src" / "not_a_package").mkdir()
    assert detect_package(tmp_path) == "app"


def test_detect_package_fails_when_ambiguous(tmp_path: Path) -> None:
    for name in ("app", "other"):
        (tmp_path / "src" / name).mkdir(parents=True)
        _ = (tmp_path / "src" / name / "__init__.py").write_text("")
    with pytest.raises(PackageNotFoundError):
        _ = detect_package(tmp_path)
