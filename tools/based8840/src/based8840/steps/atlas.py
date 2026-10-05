"""`atlas migrate validate` (opt-in): atlas.sum matches the migrations and they replay cleanly."""

from pathlib import Path
from typing import Final

from based8840.findings import Finding, Severity
from based8840.steps.command import CommandOutput

CONFIG_FILE: Final = "atlas.hcl"
ERROR_PREFIX: Final = "Error:"


def command(env: str) -> list[str]:
    return ["atlas", "migrate", "validate", "--env", env]


def parse(output: CommandOutput) -> list[Finding]:
    """Atlas prints prose, not JSON: one finding whose first line is Atlas's `Error:` line."""
    if output.exit_code == 0:
        return []
    lines: list[str] = [
        line.strip() for line in f"{output.stdout}\n{output.stderr}".splitlines() if line.strip()
    ]
    errors: list[str] = [
        line.removeprefix(ERROR_PREFIX).strip() for line in lines if line.startswith(ERROR_PREFIX)
    ]
    details: list[str] = [line for line in lines if not line.startswith(ERROR_PREFIX)]
    return [
        Finding(
            path=Path(CONFIG_FILE),
            line=0,
            column=0,
            code="BA001",
            message="\n".join([*errors, *details]) or "atlas migrate validate failed.",
            severity=Severity.ERROR,
        )
    ]
