"""`ruff format`: check mode for verify, write mode for format."""

from dataclasses import replace
from typing import Final

from based8840.findings import Finding, Severity
from based8840.steps import ruff_lint
from based8840.steps.command import CommandOutput

CHECK_COMMAND: Final = [
    "uv",
    "run",
    "--quiet",
    "ruff",
    "format",
    "--check",
    "--output-format",
    "json",
]
FORMAT_COMMAND: Final = ["uv", "run", "--quiet", "ruff", "format"]


def parse(output: CommandOutput) -> list[Finding]:
    """Same JSON as `ruff check`; one warning per spot that would change."""
    return [
        replace(
            finding,
            code="format",
            message="Not formatted. Run `based8840 format`.",
            severity=Severity.WARNING,
        )
        for finding in ruff_lint.parse(output)
    ]
