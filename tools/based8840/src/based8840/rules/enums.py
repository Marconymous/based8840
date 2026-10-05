"""BC006 enums are StrEnum whose values equal their names, BC007 states start unspecified."""

import ast
from collections.abc import Sequence
from typing import Final

from based8840.findings import Finding
from based8840.rules.common import base_names, classes_in, node_finding
from based8840.source import SourceModule

NON_STR_ENUM_BASES: Final = frozenset({"Enum", "IntEnum", "Flag", "IntFlag"})
STATE_ZERO_VALUE: Final = "STATE_UNSPECIFIED"


def check(module: SourceModule) -> list[Finding]:
    return [finding for node in classes_in(module) for finding in _check_class(module, node)]


def _check_class(module: SourceModule, node: ast.ClassDef) -> list[Finding]:
    bases: set[str] = base_names(node)
    if bases & NON_STR_ENUM_BASES:
        return [
            node_finding(
                module=module,
                node=node,
                code="BC006",
                message=f"`{node.name}` must be a StrEnum.",
            )
        ]
    if "StrEnum" not in bases:
        return []
    members: list[ast.Assign] = _members(node)
    value_findings: list[Finding] = [
        node_finding(
            module=module,
            node=member,
            code="BC006",
            message=f'`{_member_name(member)}` must have the value "{_member_name(member)}".',
        )
        for member in members
        if not _value_equals_name(member)
    ]
    return [*value_findings, *_state_findings(module, node, members)]


def _state_findings(
    module: SourceModule, node: ast.ClassDef, members: Sequence[ast.Assign]
) -> list[Finding]:
    if not node.name.endswith("State"):
        return []
    if members and _member_name(members[0]) == STATE_ZERO_VALUE:
        return []
    return [
        node_finding(
            module=module,
            node=node,
            code="BC007",
            message=f"State enum `{node.name}` must start with {STATE_ZERO_VALUE}.",
        )
    ]


def _members(node: ast.ClassDef) -> list[ast.Assign]:
    return [
        statement
        for statement in node.body
        if isinstance(statement, ast.Assign)
        and len(statement.targets) == 1
        and _member_name(statement)
        and not _member_name(statement).startswith("_")
    ]


def _member_name(statement: ast.Assign) -> str:
    target: ast.expr = statement.targets[0]
    return target.id if isinstance(target, ast.Name) else ""


def _value_equals_name(member: ast.Assign) -> bool:
    return isinstance(member.value, ast.Constant) and member.value.value == _member_name(member)
