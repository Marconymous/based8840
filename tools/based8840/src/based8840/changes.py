"""Files changed against a branch, for `verify --changed`."""

from pathlib import Path
from typing import Final

from based8840.errors import ChangedFilesError
from based8840.steps.command import CommandOutput, run_command

# `--relative` limits the diff to the project and prints paths relative to it.
DIFF_COMMAND: Final = ["git", "diff", "--name-only", "--relative", "--merge-base"]
UNTRACKED_COMMAND: Final = ["git", "ls-files", "--others", "--exclude-standard"]


def changed_files(project_dir: Path, *, base: str) -> frozenset[Path]:
    """Committed, staged, unstaged and untracked changes since the merge base with `base`.

    Paths are relative to `project_dir`; deleted files are left out.
    """
    diff: CommandOutput = run_command([*DIFF_COMMAND, base], cwd=project_dir)
    untracked: CommandOutput = run_command(UNTRACKED_COMMAND, cwd=project_dir)
    failed: CommandOutput | None = next(
        (output for output in (diff, untracked) if output.exit_code != 0), None
    )
    if failed is not None:
        raise ChangedFilesError(
            f"Cannot list files changed against `{base}`: {failed.tail(lines=3)}"
        )
    paths: set[Path] = {
        Path(line) for line in f"{diff.stdout}\n{untracked.stdout}".splitlines() if line.strip()
    }
    return frozenset(path for path in paths if (project_dir / path).is_file())


def repo_prefix(project_dir: Path) -> str:
    """Project path inside its git repository (`examples/library/`), empty outside a repo."""
    output: CommandOutput = run_command(["git", "rev-parse", "--show-prefix"], cwd=project_dir)
    return output.stdout.strip() if output.exit_code == 0 else ""
