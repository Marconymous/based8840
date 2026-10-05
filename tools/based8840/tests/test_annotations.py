"""Tests for GitHub annotations and the JSON report."""

from pathlib import Path

from based8840.annotations import github_annotations, json_report
from based8840.findings import Finding, Severity, StepOutcome, StepResult
from based8840.steps.json_values import load_json
from tests.helpers import dig


def result(*findings: Finding, error_output: str = "") -> StepResult:
    return StepResult(
        name="lint",
        outcome=StepOutcome(findings=list(findings), error_output=error_output),
        duration_seconds=1.23456,
    )


def finding(*, line: int, message: str, severity: Severity) -> Finding:
    return Finding(
        path=Path("src/app/a.py"),
        line=line,
        column=5,
        code="PLR1702",
        message=message,
        severity=severity,
    )


def test_annotation_has_repo_path_location_and_section() -> None:
    lines = github_annotations(
        [result(finding(line=3, message="Too deep", severity=Severity.ERROR))],
        path_prefix="examples/x/",
    )
    assert lines == [
        "::error file=examples/x/src/app/a.py,line=3,col=5,title=PLR1702::Too deep (§4 Never nest)"
    ]


def test_annotation_escapes_and_omits_line_zero() -> None:
    lines = github_annotations(
        [result(finding(line=0, message="50%\nnext", severity=Severity.WARNING))],
        path_prefix="",
    )
    assert lines == ["::warning file=src/app/a.py,title=PLR1702::50%25%0Anext (§4 Never nest)"]


def test_crashed_step_becomes_an_error_annotation() -> None:
    lines = github_annotations([result(error_output="boom: x, y")], path_prefix="")
    assert lines == ["::error title=lint failed to run::boom: x, y"]


def test_json_report_round_trips() -> None:
    text = json_report(
        [result(finding(line=3, message="Too deep", severity=Severity.ERROR))],
        project_dir=Path("/p"),
    )
    report: object = load_json(text)
    assert dig(report, "passed") is False
    assert dig(report, "project_dir") == "/p"
    assert dig(report, "steps", 0, "status") == "FAILED"
    assert dig(report, "steps", 0, "duration_seconds") == 1.235
    assert dig(report, "steps", 0, "findings", 0) == {
        "path": "src/app/a.py",
        "line": 3,
        "column": 5,
        "code": "PLR1702",
        "message": "Too deep",
        "severity": "ERROR",
        "section": "§4 Never nest",
    }


def test_json_report_passes_without_findings() -> None:
    assert dig(load_json(json_report([result()], project_dir=Path("/p"))), "passed") is True
