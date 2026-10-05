"""Which AGENTS.md section each rule code enforces, and what no tool can check."""

from typing import Final

from based8840.catalog import RULES

# Codes of ruff, basedpyright and pytest; based8840's own codes live in catalog.RULES.
# Keys are exact codes or code prefixes; the longest matching key wins.
SECTIONS: Final = {
    "format": "§1 Format",
    "FAILED": "§9 Testing",
    "ERROR": "§9 Testing",
    "C901": "§2 Small functions",
    "PLR0915": "§2 Small functions",
    "ANN": "§3 Typing",
    "ANN401": "§3 No Any",
    "reportAny": "§3 No Any",
    "reportExplicitAny": "§3 No Any",
    "UP": "§3 Modern syntax",
    "N": "§3 Naming",
    "TID252": "§3 Absolute imports",
    "PGH": "§3 Ignore comments",
    "reportIgnoreCommentWithoutRule": "§3 Ignore comments",
    "PLR1702": "§4 Never nest",
    "PTH": "§4 pathlib",
    "DTZ": "§4 Timezone-aware datetimes",
    "T20": "§4 Logging, not print",
    "B006": "§4 No mutable defaults",
    "F403": "§4 No wildcard imports",
    "D100": "§4 Docstrings",
    "BLE": "§5 Errors",
    "S110": "§5 Errors",
    "E722": "§5 Errors",
    "B904": "§5 Errors",
    "TID251": "§7 Banned imports",
    "ASYNC": "§7 Fully async",
}

MANUAL_REVIEW: Final = [
    "§2 KISS / YAGNI, caller orchestrates, no hidden side effects",
    "§2 Avoid default parameter values",
    "§4 Docstrings and comments explain why, not what",
    "§5 Services raise domain exceptions, one handler maps them",
    "§6 Secrets only from env, behavior keyed on named settings",
    "§7 Timeouts, bounded retries, no secrets or personal data in logs",
    "§8 AIP resource names, methods, pagination, field masks, errors",
    "§9 New behavior has a test, bug fixes start with a failing one",
]


def section_for(code: str) -> str:
    """AGENTS.md section for a rule code, or an empty string when the rule maps to none."""
    if code in RULES:
        return RULES[code].section
    matches: list[str] = [key for key in SECTIONS if code.startswith(key)]
    return SECTIONS[max(matches, key=len)] if matches else ""
