"""Tests for the tool output parsers, on canned output."""

import json
from pathlib import Path

from based8840.findings import Finding, Severity
from based8840.steps import basedpyright, pytest, ruff_format, ruff_lint
from based8840.steps.command import CommandOutput, relative_path


def output(stdout: str, *, exit_code: int) -> CommandOutput:
    return CommandOutput(exit_code=exit_code, stdout=stdout, stderr="")


def test_ruff_format_reports_unformatted_spots_as_warnings() -> None:
    stdout: str = json.dumps(
        [
            {
                "code": "unformatted",
                "message": "File would be reformatted",
                "filename": "/project/src/app/a.py",
                "location": {"row": 7, "column": 3},
            }
        ]
    )
    findings: list[Finding] = ruff_format.parse(output(stdout, exit_code=1))
    assert [(f.code, f.line, f.severity) for f in findings] == [("format", 7, Severity.WARNING)]


def test_ruff_lint_reads_code_location_and_message() -> None:
    stdout: str = json.dumps(
        [
            {
                "code": "PLR1702",
                "message": "Too many nested blocks (3 > 2)",
                "filename": "/project/src/app/a.py",
                "location": {"row": 4, "column": 5},
            },
            {"code": None, "message": "SyntaxError", "filename": "/project/x.py", "location": {}},
        ]
    )
    findings: list[Finding] = ruff_lint.parse(output(stdout, exit_code=1))
    assert [(f.code, f.line, f.column) for f in findings] == [("PLR1702", 4, 5), ("syntax", 0, 0)]


def test_ruff_lint_returns_nothing_for_non_json_output() -> None:
    assert ruff_lint.parse(output("error: failed to parse pyproject.toml", exit_code=2)) == []


def test_basedpyright_converts_positions_and_skips_information() -> None:
    diagnostic: dict[str, object] = {
        "file": "/project/src/app/a.py",
        "severity": "error",
        "message": "Type of x is Any",
        "rule": "reportAny",
        "range": {"start": {"line": 9, "character": 0}},
    }
    information: dict[str, object] = {**diagnostic, "severity": "information"}
    stdout: str = json.dumps({"generalDiagnostics": [diagnostic, information]})
    findings: list[Finding] = basedpyright.parse(output(stdout, exit_code=1))
    assert [(f.code, f.line, f.column, f.severity) for f in findings] == [
        ("reportAny", 10, 1, Severity.ERROR)
    ]


def test_pytest_reads_the_short_summary() -> None:
    stdout = (
        "..F\n"
        "FAILED tests/test_a.py::test_one - AssertionError: assert 1 == 2\n"
        "ERROR tests/test_b.py - ImportError: no module\n"
        "1 failed, 2 passed, 1 error in 0.1s\n"
    )
    findings: list[Finding] = pytest.parse(output(stdout, exit_code=1))
    assert [(f.code, str(f.path), f.message) for f in findings] == [
        ("FAILED", "tests/test_a.py", "test_one: AssertionError: assert 1 == 2"),
        ("ERROR", "tests/test_b.py", "collection: ImportError: no module"),
    ]


def test_relative_path_shortens_paths_inside_the_project(tmp_path: Path) -> None:
    inside: str = str(tmp_path / "src" / "a.py")
    assert relative_path(inside, project_dir=tmp_path.resolve()) == Path("src/a.py")
    assert relative_path("src/a.py", project_dir=tmp_path) == Path("src/a.py")


def test_command_output_tail_keeps_the_last_lines() -> None:
    command_output = CommandOutput(exit_code=1, stdout="a\nb\nc", stderr="d")
    assert command_output.tail(lines=2) == "c\nd"
