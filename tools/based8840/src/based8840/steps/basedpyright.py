"""`basedpyright` with JSON output."""

from collections.abc import Mapping
from pathlib import Path
from typing import Final

from based8840.findings import Finding, Severity
from based8840.steps.command import CommandOutput
from based8840.steps.json_values import as_int, as_list, as_mapping, as_str, load_json

COMMAND: Final = ["uv", "run", "--quiet", "basedpyright", "--outputjson"]
# "information" diagnostics are hints, not violations, so they are left out.
SEVERITIES: Final = {"error": Severity.ERROR, "warning": Severity.WARNING}


def parse(output: CommandOutput) -> list[Finding]:
    report: Mapping[str, object] = as_mapping(load_json(output.stdout))
    diagnostics: list[Mapping[str, object]] = [
        as_mapping(entry) for entry in as_list(report.get("generalDiagnostics"))
    ]
    return [
        _to_finding(diagnostic)
        for diagnostic in diagnostics
        if as_str(diagnostic.get("severity")) in SEVERITIES
    ]


def _to_finding(diagnostic: Mapping[str, object]) -> Finding:
    start: Mapping[str, object] = as_mapping(as_mapping(diagnostic.get("range")).get("start"))
    # basedpyright counts lines and columns from 0, editors and ruff from 1.
    return Finding(
        path=Path(as_str(diagnostic.get("file"))),
        line=as_int(start.get("line")) + 1,
        column=as_int(start.get("character")) + 1,
        code=as_str(diagnostic.get("rule")) or "basedpyright",
        message=as_str(diagnostic.get("message")),
        severity=SEVERITIES[as_str(diagnostic.get("severity"))],
    )
