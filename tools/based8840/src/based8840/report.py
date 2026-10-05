"""Renders step results to the terminal with rich."""

from collections.abc import Sequence
from itertools import groupby
from pathlib import Path
from typing import Final

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from based8840.findings import (
    Finding,
    Severity,
    StepResult,
    StepStatus,
    count_findings,
    step_status,
)
from based8840.sections import MANUAL_REVIEW, section_for

STATUS_LABELS: Final = {
    StepStatus.PASSED: Text("✓ passed ", style="green"),
    StepStatus.WARNING: Text("⚠ warning", style="yellow"),
    StepStatus.FAILED: Text("✗ failed ", style="red"),
}
SEVERITY_STYLES: Final = {Severity.ERROR: "red", Severity.WARNING: "yellow"}


def print_step(console: Console, result: StepResult) -> None:
    label: Text = STATUS_LABELS[step_status(result)]
    count: int = len(result.outcome.findings)
    console.print(
        Text.assemble(
            label.copy(),
            f"  {result.name:<8}",
            (f"{result.duration_seconds:5.1f}s", "dim"),
            (f"  {_plural(count, 'finding')}" if count else "", "dim"),
        )
    )


def print_findings(console: Console, results: Sequence[StepResult]) -> None:
    findings: list[Finding] = sorted(
        (finding for result in results for finding in result.outcome.findings),
        key=lambda finding: (str(finding.path), finding.line, finding.column),
    )
    for path, group in groupby(findings, key=lambda finding: finding.path):
        console.print()
        console.print(Text(str(path), style="bold underline"))
        console.print(_findings_table(list(group)))
    for result in results:
        if not result.outcome.error_output:
            continue
        console.print()
        console.print(
            Panel(
                Text(result.outcome.error_output),
                title=f"{result.name} output",
                border_style="red",
            )
        )


def print_summary(console: Console, results: Sequence[StepResult], *, notes: Sequence[str]) -> None:
    table: Table = Table(box=box.ROUNDED, title="based8840 verify", title_justify="left")
    table.add_column("Step")
    table.add_column("Status")
    table.add_column("Errors", justify="right")
    table.add_column("Warnings", justify="right")
    table.add_column("Time", justify="right")
    for result in results:
        table.add_row(
            result.name,
            STATUS_LABELS[step_status(result)],
            str(count_findings([result], severity=Severity.ERROR)),
            str(count_findings([result], severity=Severity.WARNING)),
            f"{result.duration_seconds:.1f}s",
        )
    console.print()
    console.print(table)
    for note in notes:
        console.print(Text(note, style="dim"))
    console.print(
        Panel(
            Text("\n".join(f"• {item}" for item in MANUAL_REVIEW), style="dim"),
            title="Needs human review (not checked)",
            title_align="left",
            border_style="dim",
        )
    )
    console.print(_verdict(results))


def _findings_table(findings: Sequence[Finding]) -> Table:
    table: Table = Table.grid(padding=(0, 2))
    table.add_column(justify="right", style="dim", no_wrap=True)
    table.add_column(no_wrap=True)
    table.add_column()
    for finding in findings:
        table.add_row(
            _location(finding),
            Text(finding.code, style=SEVERITY_STYLES[finding.severity]),
            _details(finding),
        )
    return table


def _details(finding: Finding) -> Text:
    """First line of the message (basedpyright adds indented detail lines) plus the section."""
    summary: str = finding.message.strip().splitlines()[0] if finding.message.strip() else ""
    section: str = section_for(finding.code)
    return Text.assemble(summary, (f"  {section}" if section else "", "dim italic"))


def _location(finding: Finding) -> str:
    return f"{finding.line}:{finding.column}" if finding.line else "-"


def _verdict(results: Sequence[StepResult]) -> Text:
    errors: int = count_findings(results, severity=Severity.ERROR)
    warnings: int = count_findings(results, severity=Severity.WARNING)
    crashed: list[str] = [result.name for result in results if result.outcome.error_output]
    if not errors and not warnings and not crashed:
        return Text("All checks passed.", style="bold green")
    crash_note: str = f", {', '.join(crashed)} failed to run" if crashed else ""
    counts: str = f"{_plural(errors, 'error')}, {_plural(warnings, 'warning')}"
    return Text(f"{counts}{crash_note}.", style="bold red")


def _plural(count: int, noun: str) -> str:
    return f"{count} {noun}{'' if count == 1 else 's'}"


def print_path(console: Console, *, command: str, project_dir: Path) -> None:
    console.print(Text.assemble((f"based8840 {command}", "bold"), "  ", (str(project_dir), "dim")))
