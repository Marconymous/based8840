"""Tests for the rule catalog, `explain` and `rules`."""

import re
from pathlib import Path

import pytest
from rich.console import Console

from based8840.catalog import RULE_LIST, RULES
from based8840.errors import RuleNotFoundError
from based8840.explain import explain_rule, list_rules

SOURCE_DIR = Path(__file__).parents[1] / "src" / "based8840"
EMITTED_CODE = re.compile(r'"(B[CLDA]\d{3})"')


def emitted_codes() -> set[str]:
    """Every own code a check can report, read from the source of the rules and steps."""
    sources = [path for path in SOURCE_DIR.rglob("*.py") if path.parent.name in {"rules", "steps"}]
    return {match.group(1) for path in sources for match in EMITTED_CODE.finditer(path.read_text())}


def recording_console() -> Console:
    return Console(record=True, width=120)


def test_every_emitted_code_is_in_the_catalog() -> None:
    assert emitted_codes() == set(RULES)


def test_catalog_codes_are_unique() -> None:
    assert len(RULE_LIST) == len(RULES)


def test_explain_shows_rationale_and_examples() -> None:
    console = recording_console()
    assert explain_rule("bc008", console=console) == 0
    text = console.export_text()
    assert "BC008" in text
    assert "§4 Bind each name once" in text
    assert "normalized_name" in text


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        ("PLR1702", "uv run ruff rule PLR1702"),
        ("plr1702", "§4 Never nest"),
        ("reportAny", "basedpyright"),
    ],
)
def test_explain_maps_external_codes(code: str, expected: str) -> None:
    console = recording_console()
    assert explain_rule(code, console=console) == 0
    assert expected in console.export_text()


@pytest.mark.parametrize("code", ["NOPE", "BC999", "E501"])
def test_explain_rejects_unknown_codes(code: str) -> None:
    with pytest.raises(RuleNotFoundError):
        _ = explain_rule(code, console=recording_console())


def test_rules_lists_own_and_external_codes() -> None:
    console = recording_console()
    assert list_rules(console=console) == 0
    text = console.export_text()
    assert all(rule.code in text for rule in RULE_LIST)
    assert "PLR1702" in text
