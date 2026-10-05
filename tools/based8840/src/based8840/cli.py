"""`based8840` command line: `verify` runs every deterministic check, `format` runs ruff format."""

import argparse
import sys
import time
from collections.abc import Callable, Sequence
from dataclasses import replace
from functools import partial
from pathlib import Path
from typing import Final

from rich.console import Console
from rich.text import Text

from based8840.errors import Based8840Error
from based8840.findings import Finding, StepOutcome, StepResult, StepStatus, step_status
from based8840.project import detect_package, find_project_dir
from based8840.report import print_findings, print_path, print_step, print_summary
from based8840.rules import (
    constants,
    dependencies,
    enums,
    ignores,
    layers,
    models,
    rebinding,
    signatures,
)
from based8840.source import SourceModule, load_source_modules
from based8840.steps import basedpyright, pytest, ruff_format, ruff_lint
from based8840.steps.command import CommandOutput, relative_path, run_command

COMMANDS: Final = frozenset({"verify", "format"})
DEFAULT_COMMAND: Final = "verify"
ERROR_TAIL_LINES: Final = 40
USAGE_ERROR_EXIT_CODE: Final = 2
RULE_CHECKS: Final = [
    signatures.check,
    constants.check,
    models.check,
    dependencies.check,
    enums.check,
    rebinding.check,
    ignores.check,
]

type Parser = Callable[[CommandOutput], list[Finding]]
type Action = Callable[[], StepOutcome]


class Arguments(argparse.Namespace):
    command: str
    project_dir: Path
    is_full: bool


def main() -> None:
    arguments: Arguments = parse_arguments(sys.argv[1:])
    console: Console = Console()
    try:
        exit_code: int = run(arguments, console=console)
    except Based8840Error as error:
        console.print(Text(str(error), style="bold red"))
        sys.exit(USAGE_ERROR_EXIT_CODE)
    sys.exit(exit_code)


def parse_arguments(argv: Sequence[str]) -> Arguments:
    """`verify` is the default, so `based8840` and `based8840 -f` work without naming it."""
    is_command_given: bool = bool(argv) and (argv[0] in COMMANDS or argv[0] in {"-h", "--help"})
    full_argv: list[str] = list(argv) if is_command_given else [DEFAULT_COMMAND, *argv]
    return _build_parser().parse_args(full_argv, namespace=Arguments())


def run(arguments: Arguments, *, console: Console) -> int:
    project_dir: Path = find_project_dir(arguments.project_dir.resolve())
    print_path(console, command=arguments.command, project_dir=project_dir)
    if arguments.command == "format":
        return format_project(project_dir, console=console)
    return verify_project(project_dir, is_full=arguments.is_full, console=console)


def format_project(project_dir: Path, *, console: Console) -> int:
    output: CommandOutput = run_command(ruff_format.FORMAT_COMMAND, cwd=project_dir)
    console.print(Text(output.tail(lines=ERROR_TAIL_LINES)))
    return output.exit_code


def verify_project(project_dir: Path, *, is_full: bool, console: Console) -> int:
    # Fail on a missing package before spending time on the slow steps.
    package: str = detect_package(project_dir) if is_full else ""
    modules: list[SourceModule] = load_source_modules(project_dir)
    layer_steps: dict[str, Action] = (
        {"layers": partial(_layers_outcome, modules=modules, package=package)} if is_full else {}
    )
    steps: dict[str, Action] = {
        "format": partial(_tool_outcome, ruff_format.CHECK_COMMAND, ruff_format.parse, project_dir),
        "lint": partial(_tool_outcome, ruff_lint.COMMAND, ruff_lint.parse, project_dir),
        "types": partial(_tool_outcome, basedpyright.COMMAND, basedpyright.parse, project_dir),
        "rules": partial(_rules_outcome, modules=modules),
        **layer_steps,
        "tests": partial(_tool_outcome, pytest.COMMAND, pytest.parse, project_dir),
    }
    results: list[StepResult] = [
        _execute(name=name, action=action, console=console) for name, action in steps.items()
    ]
    print_findings(console, results)
    print_summary(console, results, is_full=is_full)
    is_passed: bool = all(step_status(result) == StepStatus.PASSED for result in results)
    return 0 if is_passed else 1


def _build_parser() -> argparse.ArgumentParser:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        prog="based8840", description="Deterministic checks for the AGENTS.md rules."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    verify_parser: argparse.ArgumentParser = subparsers.add_parser(
        "verify", help="run every check without changing files (default)"
    )
    _add_project_dir(verify_parser)
    _ = verify_parser.add_argument(
        "-f", "--full", dest="is_full", action="store_true", help="also run opt-in layer checks"
    )
    format_parser: argparse.ArgumentParser = subparsers.add_parser(
        "format", help="format every file with ruff format"
    )
    _add_project_dir(format_parser)
    return parser


def _add_project_dir(parser: argparse.ArgumentParser) -> None:
    _ = parser.add_argument(
        "project_dir",
        nargs="?",
        type=Path,
        default=Path(),
        help="project directory or any directory inside it (default: current directory)",
    )


def _execute(*, name: str, action: Action, console: Console) -> StepResult:
    started: float = time.perf_counter()
    with console.status(f"Running {name}…"):
        outcome: StepOutcome = action()
    result: StepResult = StepResult(
        name=name, outcome=outcome, duration_seconds=time.perf_counter() - started
    )
    print_step(console, result)
    return result


def _tool_outcome(command: Sequence[str], parse: Parser, project_dir: Path) -> StepOutcome:
    output: CommandOutput = run_command(command, cwd=project_dir)
    findings: list[Finding] = [
        replace(finding, path=relative_path(str(finding.path), project_dir=project_dir))
        for finding in parse(output)
    ]
    # A non-zero exit without findings means the tool itself failed: show what it printed.
    has_crashed: bool = output.exit_code != 0 and not findings
    return StepOutcome(
        findings=findings,
        error_output=output.tail(lines=ERROR_TAIL_LINES) if has_crashed else "",
    )


def _rules_outcome(*, modules: Sequence[SourceModule]) -> StepOutcome:
    findings: list[Finding] = [
        finding for module in modules for check in RULE_CHECKS for finding in check(module)
    ]
    return StepOutcome(findings=findings, error_output="")


def _layers_outcome(*, modules: Sequence[SourceModule], package: str) -> StepOutcome:
    findings: list[Finding] = [
        finding for module in modules for finding in layers.check(module, package=package)
    ]
    return StepOutcome(findings=findings, error_output="")
