"""Tests for argument parsing, section mapping and step status."""

from pathlib import Path

import pytest

from based8840.cli import Arguments, parse_arguments
from based8840.findings import Finding, Severity, StepOutcome, StepResult, StepStatus, step_status
from based8840.sections import section_for


@pytest.mark.parametrize(
    ("argv", "command", "project_dir", "is_full"),
    [
        (["verify"], "verify", Path(), False),
        (["verify", "-f"], "verify", Path(), True),
        (["verify", "--full", "x"], "verify", Path("x"), True),
        (["format"], "format", Path(), False),
        (["format", "x"], "format", Path("x"), False),
        (["fix", "x"], "fix", Path("x"), False),
        (["init", "x"], "init", Path("x"), False),
    ],
)
def test_parse_arguments_reads_command_and_directory(
    argv: list[str], command: str, project_dir: Path, is_full: bool
) -> None:
    arguments: Arguments = parse_arguments(argv)
    assert arguments.command == command
    assert arguments.project_dir == project_dir
    assert getattr(arguments, "is_full", False) == is_full


def test_parse_arguments_reads_verify_options() -> None:
    arguments: Arguments = parse_arguments(
        ["verify", "-f", "--atlas-env", "dev", "--changed", "main", "--output", "json"]
    )
    assert arguments.atlas_env == "dev"
    assert arguments.changed_base == "main"
    assert arguments.output == "json"


def test_parse_arguments_reads_explain_code_and_init_force() -> None:
    assert parse_arguments(["explain", "BC008"]).code == "BC008"
    assert parse_arguments(["init", "--force"]).is_forced


@pytest.mark.parametrize(
    ("argv", "usage"),
    [
        ([], "usage: based8840 [-h] COMMAND"),
        (["-f"], "usage: based8840 [-h] COMMAND"),
        (["examples/library"], "usage: based8840 [-h] COMMAND"),
        (["verify", "--bogus"], "usage: based8840 verify"),
        (["verify", "--atlas-env", "dev"], "usage: based8840 verify"),
        (["verify", "--output", "xml"], "usage: based8840 verify"),
        (["format", "--full"], "usage: based8840 format"),
        (["fix", "--changed", "main"], "usage: based8840 fix"),
        (["explain"], "usage: based8840 explain"),
    ],
)
def test_misuse_prints_full_usage(
    argv: list[str], usage: str, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as raised:
        _ = parse_arguments(argv)
    stderr: str = capsys.readouterr().err
    assert raised.value.code == 2
    assert stderr.startswith(usage)
    assert "error:" in stderr


@pytest.mark.parametrize(
    ("code", "section"),
    [
        ("PLR1702", "§4 Never nest"),
        ("ANN401", "§3 No Any"),
        ("ANN001", "§3 Typing"),
        ("BL001", "§7 Layer rules"),
        ("reportAny", "§3 No Any"),
        ("BC008", "§4 Bind each name once"),
        ("BD003", "§10 Never weaken lint config"),
        ("FAST001", ""),
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
