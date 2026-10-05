"""`based8840 verify`: runs every check without changing files and reports all findings."""

import sys
import time
from collections.abc import Callable, Sequence, Set
from dataclasses import dataclass, replace
from functools import partial
from pathlib import Path
from typing import Final

from rich.console import Console

from based8840.annotations import github_annotations, json_report
from based8840.changes import changed_files, repo_prefix
from based8840.errors import AtlasEnvError
from based8840.findings import Finding, StepOutcome, StepResult, StepStatus, step_status
from based8840.project import detect_package
from based8840.reference import load_reference_pyproject
from based8840.report import print_findings, print_step, print_summary
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
from based8840.steps import atlas, basedpyright, config_drift, pytest, ruff_format, ruff_lint
from based8840.steps.command import CommandOutput, relative_path, run_command

ERROR_TAIL_LINES: Final = 40
OUTPUT_FORMATS: Final = ("text", "github", "json")
RULE_CHECKS: Final = [
    signatures.check,
    constants.check,
    models.check,
    dependencies.check,
    enums.check,
    rebinding.check,
    ignores.check,
]
# Steps whose findings `--changed` narrows to the changed files. The others are project-wide.
FILE_STEPS: Final = frozenset({"format", "lint", "types"})
NO_FINDINGS: Final = StepOutcome(findings=[], error_output="")

type Parser = Callable[[CommandOutput], list[Finding]]
type Action = Callable[[], StepOutcome]


@dataclass(frozen=True, slots=True)
class VerifyOptions:
    """`atlas_env` and `changed_base` are empty when the flag was not given."""

    is_full: bool
    atlas_env: str
    changed_base: str
    output: str


def verify_project(project_dir: Path, *, options: VerifyOptions, console: Console) -> int:
    # Fail on a missing package, Atlas env or branch before spending time on the slow steps.
    package: str = detect_package(project_dir) if options.is_full else ""
    atlas_env: str = _atlas_env(project_dir, options=options)
    changed: frozenset[Path] | None = (
        changed_files(project_dir, base=options.changed_base) if options.changed_base else None
    )
    steps: dict[str, Action] = _steps(
        project_dir, package=package, atlas_env=atlas_env, changed=changed
    )
    results: list[StepResult] = [
        _execute(name=name, action=action, changed=changed, console=console)
        for name, action in steps.items()
    ]
    print_findings(console, results)
    notes: list[str] = _notes(project_dir, options=options, changed=changed)
    print_summary(console, results, notes=notes)
    _write_machine_output(results, project_dir=project_dir, output=options.output)
    is_passed: bool = all(step_status(result) == StepStatus.PASSED for result in results)
    return 0 if is_passed else 1


def _steps(
    project_dir: Path, *, package: str, atlas_env: str, changed: Set[Path] | None
) -> dict[str, Action]:
    all_modules: list[SourceModule] = load_source_modules(project_dir)
    modules: list[SourceModule] = [
        module for module in all_modules if changed is None or module.path in changed
    ]
    layer_steps: dict[str, Action] = (
        {"layers": partial(_layers_outcome, modules=modules, package=package)} if package else {}
    )
    atlas_steps: dict[str, Action] = (
        {"atlas": partial(_tool_outcome, atlas.command(atlas_env), atlas.parse, project_dir)}
        if atlas_env
        else {}
    )
    return {
        "format": partial(
            _ruff_outcome, ruff_format.CHECK_COMMAND, ruff_format.parse, project_dir, changed
        ),
        "lint": partial(_ruff_outcome, ruff_lint.COMMAND, ruff_lint.parse, project_dir, changed),
        "types": partial(_tool_outcome, basedpyright.COMMAND, basedpyright.parse, project_dir),
        "config": partial(_config_outcome, project_dir),
        "rules": partial(_rules_outcome, modules=modules),
        **layer_steps,
        **atlas_steps,
        "tests": partial(_tool_outcome, pytest.COMMAND, pytest.parse, project_dir),
    }


def _atlas_env(project_dir: Path, *, options: VerifyOptions) -> str:
    """The env to validate, or empty when the Atlas step does not run."""
    has_atlas: bool = (project_dir / atlas.CONFIG_FILE).is_file()
    if options.atlas_env and not has_atlas:
        raise AtlasEnvError(f"--atlas-env given, but {project_dir} has no {atlas.CONFIG_FILE}.")
    if options.is_full and has_atlas and not options.atlas_env:
        raise AtlasEnvError(
            f"{project_dir / atlas.CONFIG_FILE} exists: pass --atlas-env <env> with --full."
        )
    return options.atlas_env


def _notes(project_dir: Path, *, options: VerifyOptions, changed: Set[Path] | None) -> list[str]:
    has_atlas: bool = (project_dir / atlas.CONFIG_FILE).is_file()
    skipped_layers: list[str] = (
        [] if options.is_full else ["Layer checks skipped. Run `based8840 verify --full`."]
    )
    skipped_atlas: list[str] = (
        [f"Atlas check skipped: no {atlas.CONFIG_FILE}."]
        if options.is_full and not has_atlas
        else []
    )
    changed_only: list[str] = (
        [f"Only files changed against {options.changed_base} ({len(changed)} files)."]
        if changed is not None
        else []
    )
    return [*skipped_layers, *skipped_atlas, *changed_only]


def _write_machine_output(results: Sequence[StepResult], *, project_dir: Path, output: str) -> None:
    """GitHub annotations and JSON go to stdout unstyled; rich would wrap or color them."""
    if output == "github":
        lines: list[str] = github_annotations(results, path_prefix=repo_prefix(project_dir))
        _ = sys.stdout.write("".join(f"{line}\n" for line in lines))
    if output == "json":
        _ = sys.stdout.write(f"{json_report(results, project_dir=project_dir)}\n")


def _execute(
    *, name: str, action: Action, changed: Set[Path] | None, console: Console
) -> StepResult:
    started: float = time.perf_counter()
    with console.status(f"Running {name}…"):
        outcome: StepOutcome = action()
    narrowed: StepOutcome = (
        _only_changed(outcome, changed=changed)
        if changed is not None and name in FILE_STEPS
        else outcome
    )
    result: StepResult = StepResult(
        name=name, outcome=narrowed, duration_seconds=time.perf_counter() - started
    )
    print_step(console, result)
    return result


def _only_changed(outcome: StepOutcome, *, changed: Set[Path]) -> StepOutcome:
    findings: list[Finding] = [finding for finding in outcome.findings if finding.path in changed]
    return replace(outcome, findings=findings)


def _ruff_outcome(
    command: Sequence[str], parse: Parser, project_dir: Path, changed: Set[Path] | None
) -> StepOutcome:
    """With `--changed`, ruff checks only the changed files; `--force-exclude` keeps excludes."""
    if changed is None:
        return _tool_outcome(command, parse, project_dir)
    paths: list[str] = sorted(str(path) for path in changed if path.suffix == ".py")
    if not paths:
        return NO_FINDINGS
    return _tool_outcome([*command, "--force-exclude", *paths], parse, project_dir)


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


def _config_outcome(project_dir: Path) -> StepOutcome:
    findings: Sequence[Finding] = config_drift.drift_findings(
        project_dir, reference=load_reference_pyproject()
    )
    return StepOutcome(findings=findings, error_output="")


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
