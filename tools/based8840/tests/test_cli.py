"""Tests for argument parsing, section mapping and step status."""

from pathlib import Path

import pytest

from based8840.cli import Arguments, parse_arguments
from based8840.findings import Finding, Severity, StepOutcome, StepResult, StepStatus, step_status
from based8840.sections import section_for


@pytest.mark.parametrize(
    ("argv", "command", "project_dir", "is_full"),
    [
        ([], "verify", Path(), False),
        (["-f"], "verify", Path(), True),
        (["examples/library"], "verify", Path("examples/library"), False),
        (["verify", "--full", "x"], "verify", Path("x"), True),
        (["format"], "format", Path(), False),
        (["format", "x"], "format", Path("x"), False),
    ],
)
def test_parse_arguments_defaults_to_verify(
    argv: list[str], command: str, project_dir: Path, is_full: bool
) -> None:
    arguments: Arguments = parse_arguments(argv)
    assert arguments.command == command
    assert arguments.project_dir == project_dir
    assert getattr(arguments, "is_full", False) == is_full


def test_format_takes_no_full_flag() -> None:
    with pytest.raises(SystemExit):
        _ = parse_arguments(["format", "--full"])


@pytest.mark.parametrize(
    ("code", "section"),
    [
        ("PLR1702", "§4 Never nest"),
        ("ANN401", "§3 No Any"),
        ("ANN001", "§3 Typing"),
        ("BL001", "§7 Layer rules"),
        ("reportAny", "§3 No Any"),
        ("E501", ""),
    ],
)
def test_section_for_uses_the_longest_prefix(code: str, section: str) -> None:
    assert section_for(code) == section


def result_with(*severities: Severity, error_output: str = "") -> StepResult:
    findings: list[Finding] = [
        Finding(path=Path("a.py"), line=1, column=1, code="X", message="m", severity=severity)
        for severity in severities
    ]
    return StepResult(
        name="step",
        outcome=StepOutcome(findings=findings, error_output=error_output),
        duration_seconds=0.0,
    )


@pytest.mark.parametrize(
    ("result", "status"),
    [
        (result_with(), StepStatus.PASSED),
        (result_with(Severity.WARNING), StepStatus.WARNING),
        (result_with(Severity.WARNING, Severity.ERROR), StepStatus.FAILED),
        (result_with(error_output="crashed"), StepStatus.FAILED),
    ],
)
def test_step_status(result: StepResult, status: StepStatus) -> None:
    assert step_status(result) == status
