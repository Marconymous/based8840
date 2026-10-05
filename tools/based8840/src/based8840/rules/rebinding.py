"""BC008: inside a function each name is bound once.

A name may be bound in sibling branches (`if`/`else`, `try`/`except`, `match` cases), because
only one of them runs. Binding it again after, or inside a block nested below, an earlier
binding is a rebind. Augmented assignment (`x += 1`) always rebinds.
"""

import ast
from collections.abc import Sequence, Set
from dataclasses import dataclass

from based8840.findings import Finding
from based8840.rules.common import FunctionNode, all_arguments, functions_in, node_finding
from based8840.source import SourceModule


@dataclass(frozen=True, slots=True)
class _Rebind:
    name: str
    statement: ast.stmt


@dataclass(frozen=True, slots=True)
class _BlockScan:
    bound: frozenset[str]
    rebinds: Sequence[_Rebind]


def check(module: SourceModule) -> list[Finding]:
    return [
        finding
        for function in functions_in(module)
        for finding in _check_function(module, function)
    ]


def _check_function(module: SourceModule, function: FunctionNode) -> list[Finding]:
    parameters: frozenset[str] = frozenset(argument.arg for argument in all_arguments(function))
    scan: _BlockScan = _scan_block(function.body, bound_before=parameters)
    return [
        node_finding(
            module=module,
            node=rebind.statement,
            code="BC008",
            message=f"`{rebind.name}` is bound again; give the new value a new name.",
        )
        for rebind in scan.rebinds
    ]


def _scan_block(statements: Sequence[ast.stmt], *, bound_before: Set[str]) -> _BlockScan:
    # Local accumulators: the scan walks statements in order and each one sees the names before it.
    bound_here: set[str] = set()
    rebinds: list[_Rebind] = []
    for statement in statements:
        visible: frozenset[str] = frozenset(bound_before | bound_here)
        direct: list[str] = _bound_names(statement)
        rebinds.extend(
            _Rebind(name=name, statement=statement) for name in direct if name in visible
        )
        children: list[_BlockScan] = [
            _scan_block(block, bound_before=visible | set(direct))
            for block in _child_blocks(statement)
        ]
        rebinds.extend(rebind for child in children for rebind in child.rebinds)
        bound_here.update(direct, *(child.bound for child in children))
    return _BlockScan(bound=frozenset(bound_here), rebinds=rebinds)


def _bound_names(statement: ast.stmt) -> list[str]:
    return [
        node.id
        for target in _binding_targets(statement)
        for node in ast.walk(target)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store) and node.id != "_"
    ]


def _binding_targets(statement: ast.stmt) -> list[ast.expr]:
    match statement:
        case ast.Assign(targets=targets):
            return targets
        case ast.AnnAssign(target=target, value=value) if value is not None:
            return [target]
        case ast.AugAssign(target=target) | ast.For(target=target) | ast.AsyncFor(target=target):
            return [target]
        case ast.With(items=items) | ast.AsyncWith(items=items):
            return [item.optional_vars for item in items if item.optional_vars is not None]
        case _:
            return []


def _child_blocks(statement: ast.stmt) -> list[Sequence[ast.stmt]]:
    """Nested statement lists. Nested functions and classes are their own scope: not included."""
    if isinstance(statement, ast.If | ast.For | ast.AsyncFor | ast.While):
        return [statement.body, statement.orelse]
    if isinstance(statement, ast.With | ast.AsyncWith):
        return [statement.body]
    if isinstance(statement, ast.Try | ast.TryStar):
        handler_bodies: list[Sequence[ast.stmt]] = [handler.body for handler in statement.handlers]
        return [statement.body, *handler_bodies, statement.orelse, statement.finalbody]
    if isinstance(statement, ast.Match):
        return [case.body for case in statement.cases]
    return []
