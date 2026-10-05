"""BC004: `Annotated[..., Depends(...)]` is written inline, never behind an alias."""

import ast

from based8840.findings import Finding
from based8840.rules.common import name_of, node_finding
from based8840.source import SourceModule


def check(module: SourceModule) -> list[Finding]:
    return [
        node_finding(
            module=module,
            node=statement,
            code="BC004",
            message="Alias for Annotated[..., Depends(...)]; write it inline instead.",
        )
        for statement in module.tree.body
        if _is_depends_alias(_aliased_value(statement))
    ]


def _aliased_value(statement: ast.stmt) -> ast.expr | None:
    if isinstance(statement, ast.Assign | ast.AnnAssign | ast.TypeAlias):
        return statement.value
    return None


def _is_depends_alias(value: ast.expr | None) -> bool:
    if not isinstance(value, ast.Subscript) or name_of(value.value) != "Annotated":
        return False
    return any(
        isinstance(node, ast.Call) and name_of(node.func) == "Depends" for node in ast.walk(value)
    )
