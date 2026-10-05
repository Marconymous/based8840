"""BC002: module- and class-level constants are annotated `Final`."""

import ast
import re
from typing import Final

from based8840.findings import Finding
from based8840.rules.common import base_names, classes_in, name_of, node_finding
from based8840.source import SourceModule

# Two characters minimum so a type variable such as `T` is not taken for a constant.
CONSTANT_NAME: Final = re.compile(r"^_?[A-Z][A-Z0-9_]+$")
TYPE_FACTORIES: Final = frozenset({"TypeVar", "ParamSpec", "TypeVarTuple", "NewType"})
ENUM_BASES: Final = frozenset({"Enum", "StrEnum", "IntEnum", "Flag", "IntFlag"})


def check(module: SourceModule) -> list[Finding]:
    class_bodies: list[list[ast.stmt]] = [
        node.body for node in classes_in(module) if not base_names(node) & ENUM_BASES
    ]
    return [
        node_finding(
            module=module,
            node=statement,
            code="BC002",
            message=f"Constant `{name}` must be annotated `Final`.",
        )
        for body in [module.tree.body, *class_bodies]
        for statement in body
        for name in _constants_without_final(statement)
    ]


def _constants_without_final(statement: ast.stmt) -> list[str]:
    if isinstance(statement, ast.AnnAssign):
        is_constant: bool = (
            isinstance(statement.target, ast.Name)
            and CONSTANT_NAME.match(statement.target.id) is not None
        )
        return [name_of(statement.target)] if is_constant and not _is_final(statement) else []
    if not isinstance(statement, ast.Assign) or _is_type_factory(statement.value):
        return []
    return [
        target.id
        for target in statement.targets
        if isinstance(target, ast.Name) and CONSTANT_NAME.match(target.id)
    ]


def _is_final(statement: ast.AnnAssign) -> bool:
    annotation: ast.expr = statement.annotation
    if isinstance(annotation, ast.Subscript):
        return name_of(annotation.value) == "Final"
    return name_of(annotation) == "Final"


def _is_type_factory(value: ast.expr) -> bool:
    return isinstance(value, ast.Call) and name_of(value.func) in TYPE_FACTORIES
