"""Runs an external tool and captures its output."""

import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from based8840.errors import ToolNotFoundError


@dataclass(frozen=True, slots=True)
class CommandOutput:
    exit_code: int
    stdout: str
    stderr: str

    def tail(self, *, lines: int) -> str:
        combined: str = f"{self.stdout}\n{self.stderr}".strip()
        return "\n".join(combined.splitlines()[-lines:])


def run_command(command: Sequence[str], *, cwd: Path) -> CommandOutput:
    try:
        completed: subprocess.CompletedProcess[str] = subprocess.run(
            command, cwd=cwd, capture_output=True, text=True, check=False
        )
    except FileNotFoundError as error:
        raise ToolNotFoundError(f"`{command[0]}` is not installed or not on PATH.") from error
    return CommandOutput(
        exit_code=completed.returncode, stdout=completed.stdout, stderr=completed.stderr
    )


def relative_path(filename: str, *, project_dir: Path) -> Path:
    """Tool output path relative to the project, so reports stay short."""
    path: Path = Path(filename)
    if not path.is_absolute():
        return path
    resolved: Path = path.resolve()
    return resolved.relative_to(project_dir) if resolved.is_relative_to(project_dir) else resolved
