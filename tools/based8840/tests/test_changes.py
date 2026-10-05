"""Tests for `--changed`: listing files changed against a branch in a local git repo."""

import subprocess
from pathlib import Path

import pytest

from based8840.changes import changed_files, repo_prefix
from based8840.errors import ChangedFilesError


def git(repo: Path, *args: str) -> None:
    _ = subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    git(tmp_path, "init", "--quiet", "--initial-branch", "main")
    git(tmp_path, "config", "user.email", "test@example.com")
    git(tmp_path, "config", "user.name", "test")
    project = tmp_path / "project"
    (project / "src").mkdir(parents=True)
    for name in ("kept.py", "edited.py", "deleted.py"):
        _ = (project / "src" / name).write_text("x = 1\n")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "--quiet", "-m", "init")
    git(tmp_path, "switch", "--quiet", "-c", "feature")
    return tmp_path


def test_changed_files_lists_edits_and_untracked_files(repo: Path) -> None:
    project = repo / "project"
    _ = (project / "src" / "edited.py").write_text("x = 2\n")
    (project / "src" / "deleted.py").unlink()
    _ = (project / "src" / "new.py").write_text("y = 1\n")
    _ = (repo / "outside.py").write_text("z = 1\n")
    assert changed_files(project, base="main") == {Path("src/edited.py"), Path("src/new.py")}


def test_changed_files_includes_commits_on_the_branch(repo: Path) -> None:
    project = repo / "project"
    _ = (project / "src" / "edited.py").write_text("x = 2\n")
    git(repo, "commit", "--quiet", "-am", "edit")
    assert changed_files(project, base="main") == {Path("src/edited.py")}


def test_changed_files_rejects_unknown_branch(repo: Path) -> None:
    with pytest.raises(ChangedFilesError, match="nope"):
        _ = changed_files(repo / "project", base="nope")


def test_repo_prefix(repo: Path, tmp_path_factory: pytest.TempPathFactory) -> None:
    assert repo_prefix(repo / "project") == "project/"
    assert repo_prefix(tmp_path_factory.mktemp("not-a-repo")) == ""
