"""`pytest`, reading failures from the short test summary (`-rfE`)."""

from pathlib import Path
from typing import Final

from based8840.findings import Finding, Severity
from based8840.steps.command import CommandOutput

COMMAND: Final = ["uv", "run", "--quiet", "pytest", "-q", "-rfE"]
OUTCOMES: Final = ("FAILED ", "ERROR ")


def parse(output: CommandOutput) -> list[Finding]:
    return [_to_finding(line) for line in output.stdout.splitlines() if line.startswith(OUTCOMES)]


def _to_finding(line: str) -> Finding:
    """`FAILED tests/test_x.py::test_y - AssertionError: ...` or `ERROR tests/test_x.py - ...`."""
    outcome, _, rest = line.partition(" ")
    node_id, _, reason = rest.partition(" - ")
    path, _, test_name = node_id.partition("::")
    return Finding(
        path=Path(path),
        line=0,
        column=0,
        code=outcome,
        message=f"{test_name or 'collection'}: {reason}" if reason else test_name,
        severity=Severity.ERROR,
    )
