"""Findings and step results shared by every check."""

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class Severity(StrEnum):
    ERROR = "ERROR"
    WARNING = "WARNING"


class StepStatus(StrEnum):
    PASSED = "PASSED"
    WARNING = "WARNING"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class Finding:
    """One violation. `path` is relative to the project directory; `line` 0 means whole file."""

    path: Path
    line: int
    column: int
    code: str
    message: str
    severity: Severity


@dataclass(frozen=True, slots=True)
class StepOutcome:
    """What a step found. `error_output` holds tool output when it failed without findings."""

    findings: Sequence[Finding]
    error_output: str


@dataclass(frozen=True, slots=True)
class StepResult:
    name: str
    outcome: StepOutcome
    duration_seconds: float


def count_findings(results: Sequence[StepResult], *, severity: Severity) -> int:
    return sum(
        1
        for result in results
        for finding in result.outcome.findings
        if finding.severity == severity
    )


def step_status(result: StepResult) -> StepStatus:
    if result.outcome.error_output or count_findings([result], severity=Severity.ERROR):
        return StepStatus.FAILED
    if result.outcome.findings:
        return StepStatus.WARNING
    return StepStatus.PASSED
