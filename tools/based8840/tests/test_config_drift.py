"""Tests for the config drift check (BD001-BD005) against the reference pyproject.toml."""

import copy
import json
import textwrap
from pathlib import Path

import pytest

from based8840.findings import Finding
from based8840.reference import load_reference_pyproject
from based8840.steps.config_drift import (
    ToolConfig,
    check,
    drift_findings,
    load_basedpyright_config,
    load_ruff_config,
)

REFERENCE = load_reference_pyproject()


def reference_tool(name: str) -> dict[str, object]:
    tool = REFERENCE["tool"]
    assert isinstance(tool, dict)
    table = tool[name]
    assert isinstance(table, dict)
    return copy.deepcopy(table)


def drift(*, ruff: dict[str, object], basedpyright: dict[str, object]) -> list[Finding]:
    return check(
        ruff=ToolConfig(path=Path("pyproject.toml"), table=ruff),
        basedpyright=ToolConfig(path=Path("pyproject.toml"), table=basedpyright),
        reference=REFERENCE,
    )


def lint(ruff: dict[str, object]) -> dict[str, object]:
    table = ruff["lint"]
    assert isinstance(table, dict)
    return table


def test_reference_config_has_no_drift() -> None:
    assert drift(ruff=reference_tool("ruff"), basedpyright=reference_tool("basedpyright")) == []


def test_dropped_rule_is_bd001() -> None:
    ruff = reference_tool("ruff")
    select = lint(ruff)["select"]
    assert isinstance(select, list)
    lint(ruff)["select"] = [code for code in select if code != "FAST"]
    findings = drift(ruff=ruff, basedpyright=reference_tool("basedpyright"))
    assert [(f.code, f.message) for f in findings] == [
        ("BD001", "Rule `FAST` from the reference is not selected.")
    ]


@pytest.mark.parametrize(
    ("select", "is_drift"),
    [
        (["ALL"], False),
        (["F"], True),  # F selects pyflakes, not FAST
        (["PL", "FAST"], False),
    ],
)
def test_selectors_match_per_linter(select: list[str], is_drift: bool) -> None:
    ruff: dict[str, object] = {
        "lint": {"select": select, "extend-select": ["E", "W", "I", "N", "UP", "B", "SIM", "C4"]}
    }
    missing = {
        f.message
        for f in drift(ruff=ruff, basedpyright=reference_tool("basedpyright"))
        if f.code == "BD001"
    }
    assert ("Rule `FAST` from the reference is not selected." in missing) == is_drift


def test_new_ignores_and_excludes_are_bd002() -> None:
    ruff = reference_tool("ruff")
    ruff["extend-exclude"] = ["legacy"]
    lint(ruff)["extend-ignore"] = ["ANN401"]
    lint(ruff)["per-file-ignores"] = {"src/shop/storage/**": ["TID251"], "src/**": ["C901"]}
    findings = drift(ruff=ruff, basedpyright=reference_tool("basedpyright"))
    assert [f.message for f in findings] == [
        "`ANN401` is ignored; the reference does not ignore it.",
        "`C901` is ignored for `src/**`; the reference never ignores it.",
        "ruff excludes `legacy`.",
    ]


@pytest.mark.parametrize(
    ("section", "key", "value", "message"),
    [
        ("mccabe", "max-complexity", 20, "`max-complexity` is 20; the reference limit is 10."),
        (
            "pylint",
            "max-nested-blocks",
            None,
            "`max-nested-blocks` is unset (ruff default 5); the reference limit is 2.",
        ),
    ],
)
def test_raised_limit_is_bd003(section: str, key: str, value: int | None, message: str) -> None:
    ruff = reference_tool("ruff")
    limits = lint(ruff)[section]
    assert isinstance(limits, dict)
    if value is None:
        del limits[key]
    else:
        limits[key] = value
    findings = drift(ruff=ruff, basedpyright=reference_tool("basedpyright"))
    assert [(f.code, f.message) for f in findings] == [("BD003", message)]


def test_lower_limit_is_fine() -> None:
    ruff = reference_tool("ruff")
    lint(ruff)["mccabe"] = {"max-complexity": 5}
    assert drift(ruff=ruff, basedpyright=reference_tool("basedpyright")) == []


def test_weakened_ruff_settings_are_bd004() -> None:
    ruff = reference_tool("ruff")
    lint(ruff)["preview"] = False
    lint(ruff)["flake8-tidy-imports"] = {"ban-relative-imports": "parents", "banned-api": {}}
    findings = drift(ruff=ruff, basedpyright=reference_tool("basedpyright"))
    assert {f.code for f in findings} == {"BD004"}
    assert len(findings) == 4


def test_renamed_orm_package_still_counts_as_banned() -> None:
    ruff = reference_tool("ruff")
    lint(ruff)["flake8-tidy-imports"] = {
        "ban-relative-imports": "all",
        "banned-api": {"shop.models.sql": {}, "asyncio.gather": {}},
    }
    assert drift(ruff=ruff, basedpyright=reference_tool("basedpyright")) == []


def test_weakened_basedpyright_is_bd005_and_bd002() -> None:
    basedpyright = reference_tool("basedpyright")
    basedpyright["typeCheckingMode"] = "basic"
    basedpyright["reportAny"] = "warning"
    del basedpyright["reportExplicitAny"]
    basedpyright["ignore"] = ["src/legacy"]
    findings = drift(ruff=reference_tool("ruff"), basedpyright=basedpyright)
    assert [(f.code, f.message) for f in findings] == [
        ("BD002", "basedpyright `ignore` contains `src/legacy`."),
        ("BD005", '`typeCheckingMode` is "basic"; the reference is "standard".'),
        ("BD005", '`reportAny` is not "error".'),
        ("BD005", '`reportExplicitAny` is not "error".'),
    ]


def test_mode_all_covers_missing_reports() -> None:
    assert drift(ruff=reference_tool("ruff"), basedpyright={"typeCheckingMode": "all"}) == []


def test_loaders_prefer_the_tool_specific_files(tmp_path: Path) -> None:
    _ = (tmp_path / "pyproject.toml").write_text("[tool.ruff]\nline-length = 1\n")
    _ = (tmp_path / "ruff.toml").write_text("line-length = 2\n")
    _ = (tmp_path / "pyrightconfig.json").write_text(json.dumps({"typeCheckingMode": "basic"}))
    assert load_ruff_config(tmp_path) == ToolConfig(
        path=Path("ruff.toml"), table={"line-length": 2}
    )
    assert load_basedpyright_config(tmp_path).path == Path("pyrightconfig.json")


def test_drift_findings_point_at_the_config_file(tmp_path: Path) -> None:
    _ = (tmp_path / "pyproject.toml").write_text(
        textwrap.dedent(
            """
            [project]
            name = "x"
            """
        )
    )
    findings = drift_findings(tmp_path, reference=REFERENCE)
    assert findings
    assert {f.path for f in findings} == {Path("pyproject.toml")}
