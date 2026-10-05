"""BL001/BL002 (opt-in): what each layer may import, and who may commit (AGENTS.md §7)."""

import ast
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, TypeGuard

from based8840.findings import Finding
from based8840.rules.common import node_finding
from based8840.source import SourceModule


@dataclass(frozen=True, slots=True)
class LayerRule:
    """`banned_imports` entries starting with `{package}` refer to the checked package."""

    directory: str
    banned_imports: Sequence[str]
    may_commit: bool


@dataclass(frozen=True, slots=True)
class _Import:
    """`from a import b` has candidates `a` and `a.b`, since `b` may be a module."""

    node: ast.stmt
    candidates: Sequence[str]


# `api/dependencies.py` wires DAOs into services, so only the routers under `api/v1` are limited.
LAYER_RULES: Final = [
    LayerRule(
        directory="api/v1",
        banned_imports=["{package}.storage", "{package}.models.sql", "sqlmodel", "sqlalchemy"],
        may_commit=False,
    ),
    LayerRule(
        directory="services",
        banned_imports=[
            "fastapi",
            "starlette",
            "{package}.api",
            "{package}.models.api",
            "{package}.storage.db",
            "sqlmodel",
            "sqlalchemy",
        ],
        may_commit=False,
    ),
    LayerRule(
        directory="storage/daos",
        banned_imports=["fastapi", "starlette", "{package}.api", "{package}.models.api"],
        may_commit=False,
    ),
    LayerRule(
        directory="integrations",
        banned_imports=["{package}.api", "{package}.services", "{package}.storage"],
        may_commit=False,
    ),
    LayerRule(
        directory="models/domain",
        banned_imports=["fastapi", "{package}.models.api", "{package}.models.sql"],
        may_commit=False,
    ),
]


def check(module: SourceModule, *, package: str) -> list[Finding]:
    rule: LayerRule | None = _rule_for(module.path, package=package)
    if rule is None:
        return []
    banned: list[str] = [name.format(package=package) for name in rule.banned_imports]
    import_findings: list[Finding] = [
        node_finding(
            module=module,
            node=found.node,
            code="BL001",
            message=f"{rule.directory}/ must not import `{_first_banned(found, banned)}`.",
        )
        for found in _imports(module.tree)
        if _first_banned(found, banned)
    ]
    commit_findings: list[Finding] = [
        node_finding(
            module=module,
            node=node,
            code="BL002",
            message=f"{rule.directory}/ must not commit; the request-scoped session does.",
        )
        for node in ast.walk(module.tree)
        if not rule.may_commit and _is_commit_call(node)
    ]
    return [*import_findings, *commit_findings]


def _rule_for(path: Path, *, package: str) -> LayerRule | None:
    package_dir: Path = Path("src") / package
    if not path.is_relative_to(package_dir):
        return None
    relative: Path = path.relative_to(package_dir)
    return next((rule for rule in LAYER_RULES if relative.is_relative_to(rule.directory)), None)


def _imports(tree: ast.Module) -> list[_Import]:
    plain: list[_Import] = [
        _Import(node=node, candidates=[alias.name])
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    ]
    from_imports: list[_Import] = [
        _Import(
            node=node,
            candidates=[node.module, *(f"{node.module}.{alias.name}" for alias in node.names)],
        )
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    ]
    return [*plain, *from_imports]


def _first_banned(found: _Import, banned: Sequence[str]) -> str:
    """The first imported module that is banned, or an empty string."""
    return next(
        (
            candidate
            for candidate in found.candidates
            for name in banned
            if candidate == name or candidate.startswith(f"{name}.")
        ),
        "",
    )


def _is_commit_call(node: ast.AST) -> TypeGuard[ast.Call]:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "commit"
    )
