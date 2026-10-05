"""`based8840 explain CODE` and `based8840 rules`: what each check enforces and why."""

import re
from typing import Final

from rich import box
from rich.console import Console, Group
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from based8840.catalog import RULE_LIST, RULES, Rule
from based8840.errors import RuleNotFoundError
from based8840.sections import SECTIONS, section_for

BASEDPYRIGHT_PREFIX: Final = "report"
# `ruff rule` takes a full code (PLR1702), not a prefix (ANN).
RUFF_CODE: Final = re.compile(r"[A-Z]+[0-9]+")
BASEDPYRIGHT_DOCS: Final = "https://docs.basedpyright.com/latest/configuration/config-files/"


def explain_rule(code: str, *, console: Console) -> int:
    rule: Rule | None = RULES.get(code.upper())
    if rule is not None:
        console.print(_rule_panel(rule))
        return 0
    # ruff codes are upper case, basedpyright rules camelCase: keep the spelling that matches.
    known_code: str = code if _is_external(code) else code.upper()
    section: str = section_for(known_code) if _is_external(known_code) else ""
    if not section:
        raise RuleNotFoundError(f"Unknown rule `{code}`. Run `based8840 rules` to list them.")
    console.print(Text.assemble((known_code, "bold"), "  ", (section, "italic")))
    console.print(_external_hint(known_code))
    return 0


def list_rules(*, console: Console) -> int:
    own: Table = Table(box=box.ROUNDED, title="based8840 rules", title_justify="left")
    own.add_column("Code", no_wrap=True)
    own.add_column("Step", no_wrap=True)
    own.add_column("Rule")
    own.add_column("AGENTS.md", no_wrap=True)
    for rule in RULE_LIST:
        own.add_row(rule.code, rule.step, rule.title, rule.section)
    external: Table = Table(
        box=box.ROUNDED, title="ruff / basedpyright / pytest codes", title_justify="left"
    )
    external.add_column("Code or prefix", no_wrap=True)
    external.add_column("AGENTS.md")
    for code, section in SECTIONS.items():
        external.add_row(code, section)
    console.print(own)
    console.print(external)
    console.print(Text("Details: based8840 explain <CODE>", style="dim"))
    return 0


def _rule_panel(rule: Rule) -> Panel:
    body: Group = Group(
        Text(rule.rationale),
        Text(),
        Text("Bad", style="bold red"),
        Syntax(rule.bad, "python", theme="ansi_dark", background_color="default"),
        Text(),
        Text("Good", style="bold green"),
        Syntax(rule.good, "python", theme="ansi_dark", background_color="default"),
    )
    title: Text = Text.assemble((rule.code, "bold"), f"  {rule.title}")
    subtitle: str = f"{rule.section} · step: {rule.step}"
    return Panel(body, title=title, title_align="left", subtitle=subtitle, subtitle_align="left")


def _is_external(code: str) -> bool:
    """A full ruff code, a basedpyright rule or an exact key; `NOPE` must not match prefix `N`."""
    return bool(
        code in SECTIONS or RUFF_CODE.fullmatch(code) or code.startswith(BASEDPYRIGHT_PREFIX)
    )


def _external_hint(code: str) -> Text:
    if code.startswith(BASEDPYRIGHT_PREFIX):
        return Text(f"basedpyright rule; see {BASEDPYRIGHT_DOCS}", style="dim")
    if RUFF_CODE.fullmatch(code):
        return Text(f"ruff rule; run `uv run ruff rule {code}` for details.", style="dim")
    return Text()
