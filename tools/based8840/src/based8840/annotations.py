"""Machine-readable verify output: GitHub Actions annotations and JSON."""

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Final

from based8840.findings import Finding, Severity, StepResult, StepStatus, step_status
from based8840.sections import section_for

COMMANDS: Final = {Severity.ERROR: "error", Severity.WARNING: "warning"}
# https://docs.github.com/actions/reference/workflow-commands-for-github-actions
DATA_ESCAPES: Final = {"%": "%25", "\r": "%0D", "\n": "%0A"}
PROPERTY_ESCAPES: Final = {**DATA_ESCAPES, ":": "%3A", ",": "%2C"}


def github_annotations(results: Sequence[StepResult], *, path_prefix: str) -> list[str]:
    """`path_prefix` turns project-relative paths into the repo-relative paths GitHub expects."""
    findings: list[str] = [
        _finding_annotation(finding, path_prefix=path_prefix)
        for result in results
        for finding in result.outcome.findings
    ]
    crashes: list[str] = [
        f"::error title={_escape(f'{result.name} failed to run', PROPERTY_ESCAPES)}"
        f"::{_escape(result.outcome.error_output, DATA_ESCAPES)}"
        for result in results
        if result.outcome.error_output
    ]
    return [*findings, *crashes]


def json_report(results: Sequence[StepResult], *, project_dir: Path) -> str:
    report: dict[str, object] = {
        "project_dir": str(project_dir),
        "passed": all(step_status(result) == StepStatus.PASSED for result in results),
        "steps": [_step_json(result) for result in results],
    }
    return json.dumps(report, indent=2, ensure_ascii=False)


def _finding_annotation(finding: Finding, *, path_prefix: str) -> str:
    location: list[str] = [f"line={finding.line}", f"col={finding.column}"] if finding.line else []
    properties: str = ",".join(
        [
            f"file={_escape(f'{path_prefix}{finding.path}', PROPERTY_ESCAPES)}",
            *location,
            f"title={_escape(finding.code, PROPERTY_ESCAPES)}",
        ]
    )
    section: str = section_for(finding.code)
    message: str = f"{finding.message} ({section})" if section else finding.message
    return f"::{COMMANDS[finding.severity]} {properties}::{_escape(message, DATA_ESCAPES)}"


def _step_json(result: StepResult) -> dict[str, object]:
    return {
        "name": result.name,
        "status": step_status(result).value,
        "duration_seconds": round(result.duration_seconds, 3),
        "error_output": result.outcome.error_output,
        "findings": [_finding_json(finding) for finding in result.outcome.findings],
    }


def _finding_json(finding: Finding) -> dict[str, object]:
    return {
        "path": str(finding.path),
        "line": finding.line,
        "column": finding.column,
        "code": finding.code,
        "message": finding.message,
        "severity": finding.severity.value,
        "section": section_for(finding.code),
    }


def _escape(text: str, escapes: Mapping[str, str]) -> str:
    # Character by character, so the `%` of an escape just written is never escaped again.
    return "".join(escapes.get(character, character) for character in text)
