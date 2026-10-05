"""`based8840 fix`: ruff's automatic fixes, then formatting, then what is still left."""

import time
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path
from typing import Final

from rich.console import Console
from rich.text import Text

from based8840.findings import Finding, StepOutcome, StepResult
from based8840.report import print_findings
from based8840.steps import ruff_format, ruff_lint
from based8840.steps.command import CommandOutput, relative_path, run_command

ERROR_TAIL_LINES: Final = 40


def fix_project(project_dir: Path, *, console: Console) -> int:
    """Fix before format, as ruff recommends: a fix such as a removed import can unformat code."""
    started: float = time.perf_counter()
    with console.status("Running ruff check --fix…"):
        _ = run_command(ruff_lint.FIX_COMMAND, cwd=project_dir)
    with console.status("Running ruff format…"):
        formatted: CommandOutput = run_command(ruff_format.FORMAT_COMMAND, cwd=project_dir)
    if formatted.exit_code != 0:
        console.print(Text(formatted.tail(lines=ERROR_TAIL_LINES)))
        return formatted.exit_code
    # Checked again after formatting so the reported positions match the files on disk.
    with console.status("Running ruff check…"):
        remaining: CommandOutput = run_command(ruff_lint.COMMAND, cwd=project_dir)
    findings: list[Finding] = [
        replace(finding, path=relative_path(str(finding.path), project_dir=project_dir))
        for finding in ruff_lint.parse(remaining)
    ]
    has_crashed: bool = remaining.exit_code != 0 and not findings
    result: StepResult = StepResult(
        name="lint",
        outcome=StepOutcome(
            findings=findings,
            error_output=remaining.tail(lines=ERROR_TAIL_LINES) if has_crashed else "",
        ),
        duration_seconds=time.perf_counter() - started,
    )
    print_findings(console, [result])
    console.print(_verdict(findings, has_crashed=has_crashed))
    return 1 if findings or has_crashed else 0


def _verdict(findings: Sequence[Finding], *, has_crashed: bool) -> Text:
    if has_crashed:
        return Text("ruff check failed to run.", style="bold red")
    if not findings:
        return Text("Fixed and formatted. No lint findings left.", style="bold green")
    return Text(
        f"Fixed and formatted. {len(findings)} lint findings need a manual fix.", style="bold red"
    )
