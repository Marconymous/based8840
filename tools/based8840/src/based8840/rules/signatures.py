"""BC001 no tuples in signatures, BC005 parameters take read-only collection types."""

import ast
from typing import Final

from based8840.findings import Finding
from based8840.rules.common import FunctionNode, all_arguments, functions_in, name_of, node_finding
from based8840.source import SourceModule

TUPLE_NAMES: Final = frozenset({"tuple", "Tuple"})
# `Set` is left out on purpose: `collections.abc.Set` is the read-only type the rule asks for.
READ_ONLY_REPLACEMENTS: Final = {
    "list": "Sequence",
    "List": "Sequence",
    "dict": "Mapping",
    "Dict": "Mapping",
    "set": "Set",
}


def check(module: SourceModule) -> list[Finding]:
    return [
        finding
        for function in functions_in(module)
        for finding in _function_findings(module, function)
    ]


def _function_findings(module: SourceModule, function: FunctionNode) -> list[Finding]:
    parameter_findings: list[Finding] = [
        finding
        for argument in all_arguments(function)
        for finding in _parameter_findings(module, argument)
    ]
    return [*_return_findings(module, function), *parameter_findings]


def _return_findings(module: SourceModule, function: FunctionNode) -> list[Finding]:
    if function.returns is None or not _mentions_tuple(function.returns):
        return []
    return [
        node_finding(
            module=module,
            node=function,
            code="BC001",
            message=f"`{function.name}` returns a tuple; return a frozen model or a list.",
        )
    ]


def _parameter_findings(module: SourceModule, argument: ast.arg) -> list[Finding]:
    if argument.annotation is None:
        return []
    tuple_findings: list[Finding] = (
        [
            node_finding(
                module=module,
                node=argument,
                code="BC001",
                message=f"Parameter `{argument.arg}` takes a tuple; use a frozen model.",
            )
        ]
        if _mentions_tuple(argument.annotation)
        else []
    )
    mutable_findings: list[Finding] = [
        node_finding(
            module=module,
            node=argument,
            code="BC005",
            message=(
                f"Parameter `{argument.arg}` is `{name}`; "
                f"take a read-only `{READ_ONLY_REPLACEMENTS[name]}`."
            ),
        )
        for name in _mutable_collections(argument.annotation)
    ]
    return [*tuple_findings, *mutable_findings]


def _mentions_tuple(annotation: ast.expr) -> bool:
    return any(
        name_of(node) in TUPLE_NAMES for node in ast.walk(annotation) if isinstance(node, ast.expr)
    )


def _mutable_collections(annotation: ast.expr) -> list[str]:
    """Mutable collection types at the top level of the annotation, including union members."""
    names: list[str] = [name_of(_unsubscripted(member)) for member in _union_members(annotation)]
    return [name for name in names if name in READ_ONLY_REPLACEMENTS]


def _union_members(annotation: ast.expr) -> list[ast.expr]:
    if isinstance(annotation, ast.BinOp) and isinstance(annotation.op, ast.BitOr):
        return [*_union_members(annotation.left), *_union_members(annotation.right)]
    return [annotation]


def _unsubscripted(annotation: ast.expr) -> ast.expr:
    return annotation.value if isinstance(annotation, ast.Subscript) else annotation
