"""BC003: pydantic models are frozen and reject unknown fields."""

import ast
from typing import Final

from based8840.findings import Finding
from based8840.rules.common import base_names, classes_in, node_finding
from based8840.source import SourceModule

# Settings read the environment and ORM tables must stay mutable, so both are exempt.
EXEMPT_BASES: Final = frozenset({"BaseSettings", "SQLModel"})


def check(module: SourceModule) -> list[Finding]:
    """Only direct `BaseModel` subclasses: subclasses of project models inherit their config."""
    models: list[ast.ClassDef] = [
        node
        for node in classes_in(module)
        if "BaseModel" in base_names(node) and not base_names(node) & EXEMPT_BASES
    ]
    return [
        node_finding(
            module=module,
            node=model,
            code="BC003",
            message=(
                f'`{model.name}` needs model_config = ConfigDict(frozen=True, extra="forbid").'
            ),
        )
        for model in models
        if not any(_is_frozen_and_forbids_extra(value) for value in _model_configs(model))
    ]


def _model_configs(model: ast.ClassDef) -> list[ast.expr]:
    assigns: list[ast.expr | None] = [
        statement.value
        for statement in model.body
        if isinstance(statement, ast.Assign | ast.AnnAssign) and _targets_model_config(statement)
    ]
    return [value for value in assigns if value is not None]


def _targets_model_config(statement: ast.Assign | ast.AnnAssign) -> bool:
    targets: list[ast.expr] = (
        statement.targets if isinstance(statement, ast.Assign) else [statement.target]
    )
    return any(isinstance(target, ast.Name) and target.id == "model_config" for target in targets)


def _is_frozen_and_forbids_extra(value: ast.expr) -> bool:
    if not isinstance(value, ast.Call):
        return False
    keywords: dict[str, object] = {
        keyword.arg: keyword.value.value
        for keyword in value.keywords
        if keyword.arg is not None and isinstance(keyword.value, ast.Constant)
    }
    return keywords.get("frozen") is True and keywords.get("extra") == "forbid"
