"""BD001 to BD005: the project's ruff and basedpyright config must not be weaker than the reference.

Each tool's config is read from the file that tool actually uses: ruff from `ruff.toml` /
`.ruff.toml` before `pyproject.toml`, basedpyright from `pyrightconfig.json` before
`pyproject.toml`. Findings point at that file (line 0: the whole file).
"""

import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from based8840.findings import Finding, Severity
from based8840.steps.json_values import as_list, as_mapping, as_str, load_json

RUFF_FILES: Final = ("ruff.toml", ".ruff.toml")
BASEDPYRIGHT_FILE: Final = "pyrightconfig.json"
PYPROJECT: Final = "pyproject.toml"
# Where ruff keeps each limit, and ruff's value when the key is missing.
LIMITS: Final = {
    "max-complexity": ("mccabe", 10),
    "max-nested-blocks": ("pylint", 5),
    "max-statements": ("pylint", 50),
}
TYPE_CHECKING_MODES: Final = ["off", "basic", "standard", "strict", "recommended", "all"]
# basedpyright's own default mode.
DEFAULT_TYPE_CHECKING_MODE: Final = "recommended"
# Banned-api entries naming the ORM package match by suffix: the package may not be `app`.
ORM_MODULE_SUFFIX: Final = "models.sql"
# Linters whose rules carry an extra category letter: `PL` selects PLC, PLE, PLR and PLW.
CATEGORY_LINTERS: Final = frozenset({"PL"})


@dataclass(frozen=True, slots=True)
class _Drift:
    code: str
    message: str


@dataclass(frozen=True, slots=True)
class ToolConfig:
    """One tool's settings table and the file it came from, relative to the project."""

    path: Path
    table: Mapping[str, object]


def load_ruff_config(project_dir: Path) -> ToolConfig:
    for name in RUFF_FILES:
        if (project_dir / name).is_file():
            return ToolConfig(path=Path(name), table=_load_toml(project_dir / name))
    pyproject: Mapping[str, object] = _load_toml(project_dir / PYPROJECT)
    return ToolConfig(path=Path(PYPROJECT), table=_get(pyproject, "tool", "ruff"))


def load_basedpyright_config(project_dir: Path) -> ToolConfig:
    json_config: Path = project_dir / BASEDPYRIGHT_FILE
    if json_config.is_file():
        table: Mapping[str, object] = as_mapping(load_json(json_config.read_text(encoding="utf-8")))
        return ToolConfig(path=Path(BASEDPYRIGHT_FILE), table=table)
    pyproject: Mapping[str, object] = _load_toml(project_dir / PYPROJECT)
    return ToolConfig(path=Path(PYPROJECT), table=_get(pyproject, "tool", "basedpyright"))


def check(
    *, ruff: ToolConfig, basedpyright: ToolConfig, reference: Mapping[str, object]
) -> list[Finding]:
    """`reference` is the parsed reference pyproject.toml."""
    reference_ruff: Mapping[str, object] = _get(reference, "tool", "ruff")
    reference_basedpyright: Mapping[str, object] = _get(reference, "tool", "basedpyright")
    ruff_messages: list[_Drift] = [
        *_missing_selections(ruff.table, reference_ruff),
        *_new_ruff_ignores(ruff.table, reference_ruff),
        *_raised_limits(ruff.table, reference_ruff),
        *_weakened_ruff_settings(ruff.table, reference_ruff),
    ]
    basedpyright_messages: list[_Drift] = [
        *_new_basedpyright_ignores(basedpyright.table, reference_basedpyright),
        *_weakened_basedpyright(basedpyright.table, reference_basedpyright),
    ]
    return [
        *(_finding(ruff.path, drift) for drift in ruff_messages),
        *(_finding(basedpyright.path, drift) for drift in basedpyright_messages),
    ]


def _missing_selections(
    ruff: Mapping[str, object], reference: Mapping[str, object]
) -> list[_Drift]:
    selected: list[str] = [*_lint_strings(ruff, "select"), *_lint_strings(ruff, "extend-select")]
    return [
        _Drift(code="BD001", message=f"Rule `{code}` from the reference is not selected.")
        for code in _lint_strings(reference, "select")
        if not any(_selects(selection, code) for selection in selected)
    ]


def _new_ruff_ignores(ruff: Mapping[str, object], reference: Mapping[str, object]) -> list[_Drift]:
    allowed_ignores: set[str] = set(_lint_strings(reference, "ignore"))
    ignored: list[str] = [*_lint_strings(ruff, "ignore"), *_lint_strings(ruff, "extend-ignore")]
    # Per-file globs are compared by code only, so a package not named `app` is fine.
    allowed_per_file: set[str] = {
        code for codes in _per_file_ignores(reference).values() for code in codes
    }
    excludes: list[str] = [
        *_strings(ruff, "exclude"),
        *_strings(ruff, "extend-exclude"),
        *_strings(ruff, "lint", "exclude"),
    ]
    return [
        *(
            _Drift(code="BD002", message=f"`{code}` is ignored; the reference does not ignore it.")
            for code in ignored
            if code not in allowed_ignores
        ),
        *(
            _Drift(
                code="BD002",
                message=f"`{code}` is ignored for `{glob}`; the reference never ignores it.",
            )
            for glob, codes in _per_file_ignores(ruff).items()
            for code in codes
            if code not in allowed_per_file
        ),
        *(_Drift(code="BD002", message=f"ruff excludes `{pattern}`.") for pattern in excludes),
    ]


def _raised_limits(ruff: Mapping[str, object], reference: Mapping[str, object]) -> list[_Drift]:
    drifts: list[_Drift | None] = [_raised_limit(ruff, reference, key=key) for key in LIMITS]
    return [drift for drift in drifts if drift is not None]


def _raised_limit(
    ruff: Mapping[str, object], reference: Mapping[str, object], *, key: str
) -> _Drift | None:
    section, ruff_default = LIMITS[key]
    reference_value: object = _get_value(reference, "lint", section, key)
    value: object = _get_value(ruff, "lint", section, key)
    effective: int = value if isinstance(value, int) else ruff_default
    if not isinstance(reference_value, int) or effective <= reference_value:
        return None
    shown: str = str(value) if isinstance(value, int) else f"unset (ruff default {effective})"
    return _Drift(
        code="BD003", message=f"`{key}` is {shown}; the reference limit is {reference_value}."
    )


def _weakened_ruff_settings(
    ruff: Mapping[str, object], reference: Mapping[str, object]
) -> list[_Drift]:
    findings: list[_Drift] = []
    is_preview_needed: bool = _get_value(reference, "lint", "preview") is True
    is_preview_on: bool = _get_value(ruff, "lint", "preview") is True or ruff.get("preview") is True
    if is_preview_needed and not is_preview_on:
        findings.append(
            _Drift(code="BD004", message="`preview` is off; PLR1702 (never nest) needs it.")
        )
    tidy: Mapping[str, object] = _get(ruff, "lint", "flake8-tidy-imports")
    reference_tidy: Mapping[str, object] = _get(reference, "lint", "flake8-tidy-imports")
    reference_ban: object = reference_tidy.get("ban-relative-imports")
    if reference_ban is not None and tidy.get("ban-relative-imports") != reference_ban:
        findings.append(
            _Drift(
                code="BD004", message=f'`ban-relative-imports` is not "{as_str(reference_ban)}".'
            )
        )
    banned: Mapping[str, object] = as_mapping(tidy.get("banned-api"))
    findings.extend(
        _Drift(code="BD004", message=f"banned-api entry `{module}` is missing.")
        for module in as_mapping(reference_tidy.get("banned-api"))
        if not _is_banned(module, banned)
    )
    return findings


def _new_basedpyright_ignores(
    basedpyright: Mapping[str, object], reference: Mapping[str, object]
) -> list[_Drift]:
    return [
        _Drift(code="BD002", message=f"basedpyright `{key}` contains `{pattern}`.")
        for key in ("exclude", "ignore")
        for pattern in _strings(basedpyright, key)
        if pattern not in _strings(reference, key)
    ]


def _weakened_basedpyright(
    basedpyright: Mapping[str, object], reference: Mapping[str, object]
) -> list[_Drift]:
    mode: str = as_str(basedpyright.get("typeCheckingMode")) or DEFAULT_TYPE_CHECKING_MODE
    reference_mode: str = as_str(reference.get("typeCheckingMode"))
    weaker_mode: list[_Drift] = (
        [
            _Drift(
                code="BD005",
                message=f'`typeCheckingMode` is "{mode}"; the reference is "{reference_mode}".',
            )
        ]
        if _mode_rank(mode) < _mode_rank(reference_mode)
        else []
    )
    # Mode "all" turns every report into an error, so missing keys are fine there.
    lowered: list[_Drift] = [
        _Drift(code="BD005", message=f'`{key}` is not "error".')
        for key, value in reference.items()
        if key.startswith("report") and value == "error"
        if not _is_error(basedpyright.get(key), mode=mode)
    ]
    return [*weaker_mode, *lowered]


def _selects(selection: str, code: str) -> bool:
    """Ruff selectors match per linter: `F` selects F401 but not FAST, `PL` selects PLR1702."""
    if selection == "ALL":
        return True
    is_same_linter: bool = _letters(selection) == _letters(code) or selection in CATEGORY_LINTERS
    return code.startswith(selection) and is_same_linter


def _letters(code: str) -> str:
    return code.rstrip("0123456789")


def _is_error(value: object, *, mode: str) -> bool:
    if value is None:
        return mode == "all"
    return value in ("error", True)


def _mode_rank(mode: str) -> int:
    return TYPE_CHECKING_MODES.index(mode) if mode in TYPE_CHECKING_MODES else 0


def _is_banned(module: str, banned: Mapping[str, object]) -> bool:
    if module.endswith(ORM_MODULE_SUFFIX):
        return any(entry.endswith(ORM_MODULE_SUFFIX) for entry in banned)
    return module in banned


def _per_file_ignores(ruff: Mapping[str, object]) -> dict[str, list[str]]:
    tables: list[Mapping[str, object]] = [
        as_mapping(_lint_value(ruff, "per-file-ignores")),
        as_mapping(_lint_value(ruff, "extend-per-file-ignores")),
    ]
    return {
        glob: [as_str(code) for code in as_list(codes)]
        for table in tables
        for glob, codes in table.items()
    }


def _lint_strings(ruff: Mapping[str, object], key: str) -> list[str]:
    return [as_str(item) for item in as_list(_lint_value(ruff, key))]


def _lint_value(ruff: Mapping[str, object], key: str) -> object:
    """Ruff still reads lint keys at the top level (deprecated); `lint.` wins."""
    lint: Mapping[str, object] = as_mapping(ruff.get("lint"))
    return lint[key] if key in lint else ruff.get(key)


def _strings(table: Mapping[str, object], *keys: str) -> list[str]:
    return [as_str(item) for item in as_list(_get_value(table, *keys))]


def _get(table: Mapping[str, object], *keys: str) -> Mapping[str, object]:
    return as_mapping(_get_value(table, *keys))


def _get_value(table: Mapping[str, object], *keys: str) -> object:
    parents: list[Mapping[str, object]] = [table]
    for key in keys[:-1]:
        parents.append(as_mapping(parents[-1].get(key)))
    return parents[-1].get(keys[-1])


def _load_toml(path: Path) -> Mapping[str, object]:
    return tomllib.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def _finding(path: Path, drift: _Drift) -> Finding:
    return Finding(
        path=path,
        line=0,
        column=0,
        code=drift.code,
        message=drift.message,
        severity=Severity.ERROR,
    )


def drift_findings(project_dir: Path, *, reference: Mapping[str, object]) -> Sequence[Finding]:
    return check(
        ruff=load_ruff_config(project_dir),
        basedpyright=load_basedpyright_config(project_dir),
        reference=reference,
    )
