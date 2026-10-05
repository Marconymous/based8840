"""`ruff check` with JSON output."""

from collections.abc import Mapping
from pathlib import Path
from typing import Final

from based8840.findings import Finding, Severity
from based8840.steps.command import CommandOutput
from based8840.steps.json_values import as_int, as_list, as_mapping, as_str, load_json

# --no-fix: verify never changes files, even when the project sets `fix = true`.
COMMAND: Final = ["uv", "run", "--quiet", "ruff", "check", "--no-fix", "--output-format", "json"]


def parse(output: CommandOutput) -> list[Finding]:
    entries: list[object] = as_list(load_json(output.stdout))
    return [_to_finding(as_mapping(entry)) for entry in entries]


def _to_finding(entry: Mapping[str, object]) -> Finding:
    location: Mapping[str, object] = as_mapping(entry.get("location"))
    return Finding(
        path=Path(as_str(entry.get("filename"))),
        line=as_int(location.get("row")),
        column=as_int(location.get("column")),
        code=as_str(entry.get("code")) or "syntax",
        message=as_str(entry.get("message")),
        severity=Severity.ERROR,
    )
