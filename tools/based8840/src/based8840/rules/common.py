"""Small AST helpers shared by the rules."""

import ast

from based8840.findings import Finding, Severity
from based8840.source import SourceModule

type FunctionNode = ast.FunctionDef | ast.AsyncFunctionDef


def node_finding(
    *, module: SourceModule, node: ast.stmt | ast.expr | ast.arg, code: str, message: str
) -> Finding:
    return Finding(
        path=module.path,
        line=node.lineno,
        column=node.col_offset + 1,
        code=code,
        message=message,
        severity=Severity.ERROR,
    )


def name_of(expr: ast.expr) -> str:
    """`Final` for both `Final` and `typing.Final`; empty for anything that is not a name."""
    if isinstance(expr, ast.Name):
        return expr.id
    if isinstance(expr, ast.Attribute):
        return expr.attr
    return ""


def base_names(node: ast.ClassDef) -> set[str]:
    return {name_of(base) for base in node.bases}


def functions_in(module: SourceModule) -> list[FunctionNode]:
    return [
        node
        for node in ast.walk(module.tree)
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    ]


def classes_in(module: SourceModule) -> list[ast.ClassDef]:
    return [node for node in ast.walk(module.tree) if isinstance(node, ast.ClassDef)]


def all_arguments(function: FunctionNode) -> list[ast.arg]:
    arguments: ast.arguments = function.args
    variadic: list[ast.arg] = [
        arg for arg in (arguments.vararg, arguments.kwarg) if arg is not None
    ]
    return [*arguments.posonlyargs, *arguments.args, *arguments.kwonlyargs, *variadic]
