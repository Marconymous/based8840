"""`based8840 init`: copies the agent files into a project and merges the reference tool config."""

import shutil
from collections.abc import Mapping, MutableMapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Final

import tomlkit
from rich.console import Console
from rich.text import Text
from tomlkit import TOMLDocument
from tomlkit.items import Array

from based8840.errors import InitConflictError, PackageNotFoundError, ProjectNotFoundError
from based8840.project import detect_package, is_project
from based8840.reference import reference_dir

COPIED_FILES: Final = [Path("AGENTS.md"), Path("CLAUDE.md"), Path(".claude/settings.json")]
HOOKS_DIR: Final = Path(".claude/hooks")
HOOK_MODE: Final = 0o755
SYMLINK: Final = Path(".github/copilot-instructions.md")
SYMLINK_TARGET: Final = Path("../AGENTS.md")
PYPROJECT: Final = "pyproject.toml"
REFERENCE_PACKAGE: Final = "app"
DEV_DEPENDENCIES: Final = "uv add --dev ruff basedpyright pytest pytest-asyncio httpx"


class ChangeKind(StrEnum):
    ADD = "ADD"
    APPEND = "APPEND"
    KEEP = "KEEP"


@dataclass(frozen=True, slots=True)
class TomlChange:
    """ADD sets `value` at `keys`, APPEND extends the list there, KEEP leaves a differing value."""

    kind: ChangeKind
    keys: Sequence[str]
    value: object
    reference_value: object


def init_project(target_dir: Path, *, is_forced: bool, console: Console) -> int:
    if not is_project(target_dir):
        raise ProjectNotFoundError(
            f"No pyproject.toml with a [project] table in {target_dir}. Run `uv init` first."
        )
    source_dir: Path = reference_dir()
    copies: list[Path] = planned_copies(source_dir)
    existing: list[Path] = [path for path in [*copies, SYMLINK] if _occupied(target_dir / path)]
    if existing and not is_forced:
        listed: str = ", ".join(str(path) for path in existing)
        raise InitConflictError(f"Already in {target_dir}: {listed}. Use --force to overwrite.")
    package: str = _package_or_reference(target_dir)
    pyproject: Path = target_dir / PYPROJECT
    reference_text: str = renamed_reference(
        (source_dir / PYPROJECT).read_text(encoding="utf-8"), package=package
    )
    target_text: str = pyproject.read_text(encoding="utf-8")
    changes: list[TomlChange] = toml_changes(
        tomlkit.parse(target_text), tomlkit.parse(reference_text), keys=[]
    )
    for path in copies:
        _copy(source_dir / path, target_dir / path)
    _link(target_dir / SYMLINK)
    _ = pyproject.write_text(apply_changes(target_text, changes=changes), encoding="utf-8")
    _print_report(console, copies=copies, changes=changes, package=package)
    return 0


def planned_copies(source_dir: Path) -> list[Path]:
    hooks: list[Path] = sorted(
        path.relative_to(source_dir) for path in (source_dir / HOOKS_DIR).iterdir()
    )
    return [*COPIED_FILES, *hooks]


def renamed_reference(reference_text: str, *, package: str) -> str:
    """Point the reference's `src/app` globs and `app.models.sql` ban at the project's package."""
    return reference_text.replace(f'"src/{REFERENCE_PACKAGE}/', f'"src/{package}/').replace(
        f'"{REFERENCE_PACKAGE}.models.sql"', f'"{package}.models.sql"'
    )


def toml_changes(target: object, reference: object, *, keys: Sequence[str]) -> list[TomlChange]:
    """What merging `reference` into `target` changes: missing keys added, lists unioned."""
    if not isinstance(target, Mapping) or not isinstance(reference, Mapping):
        return []
    return [
        change
        for key, reference_value in reference.items()
        for change in _key_changes(target, key=str(key), reference_value=reference_value, keys=keys)
    ]


def apply_changes(target_text: str, *, changes: Sequence[TomlChange]) -> str:
    # tomlkit keeps the target's comments and layout; the document is local to this function.
    document: TOMLDocument = tomlkit.parse(target_text)
    for change in changes:
        if change.kind == ChangeKind.KEEP:
            continue
        parent: MutableMapping[str, object] = _table_at(document, change.keys[:-1])
        _apply(parent, change=change)
    return tomlkit.dumps(document)


def _key_changes(
    target: Mapping[object, object],
    *,
    key: str,
    reference_value: object,
    keys: Sequence[str],
) -> list[TomlChange]:
    path: list[str] = [*keys, key]
    if key not in target:
        return [_change_of(ChangeKind.ADD, path, value=reference_value, reference=reference_value)]
    value: object = target[key]
    if isinstance(value, Mapping) and isinstance(reference_value, Mapping):
        return toml_changes(value, reference_value, keys=path)
    if isinstance(value, list) and isinstance(reference_value, list):
        missing: list[object] = [item for item in reference_value if item not in value]
        if not missing:
            return []
        return [_change_of(ChangeKind.APPEND, path, value=missing, reference=reference_value)]
    if value != reference_value:
        return [_change_of(ChangeKind.KEEP, path, value=value, reference=reference_value)]
    return []


def _change_of(
    kind: ChangeKind, keys: Sequence[str], *, value: object, reference: object
) -> TomlChange:
    return TomlChange(kind=kind, keys=keys, value=value, reference_value=reference)


def _table_at(document: TOMLDocument, keys: Sequence[str]) -> MutableMapping[str, object]:
    """Only existing tables: toml_changes adds a whole table at the first missing key."""
    tables: list[MutableMapping[str, object]] = [document]
    for key in keys:
        child: object = tables[-1][key]
        if not isinstance(child, MutableMapping):
            raise TypeError(f"`{'.'.join(keys)}` is not a table.")
        tables.append(child)
    return tables[-1]


def _apply(parent: MutableMapping[str, object], *, change: TomlChange) -> None:
    key: str = change.keys[-1]
    if change.kind == ChangeKind.ADD:
        parent[key] = change.value
        return
    existing: object = parent[key]
    if not isinstance(existing, Array) or not isinstance(change.value, list):
        return
    existing.extend(change.value)
    # One item per line keeps a long rule list readable and diffs small.
    _ = existing.multiline(True)


def _package_or_reference(target_dir: Path) -> str:
    try:
        return detect_package(target_dir)
    except PackageNotFoundError:
        return REFERENCE_PACKAGE


def _occupied(path: Path) -> bool:
    return path.exists() or path.is_symlink()


def _copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    # unlink first so --force replaces a symlink instead of writing through it.
    destination.unlink(missing_ok=True)
    _ = shutil.copy2(source, destination)
    # Wheels do not keep the executable bit, and settings.json runs the hooks directly.
    if destination.parent.name == HOOKS_DIR.name:
        destination.chmod(HOOK_MODE)


def _link(link: Path) -> None:
    link.parent.mkdir(parents=True, exist_ok=True)
    link.unlink(missing_ok=True)
    link.symlink_to(SYMLINK_TARGET)


def _print_report(
    console: Console, *, copies: Sequence[Path], changes: Sequence[TomlChange], package: str
) -> None:
    console.print(Text("Copied", style="bold"))
    for path in [*copies, SYMLINK]:
        console.print(f"  {path}")
    console.print(Text(f"Merged into {PYPROJECT}", style="bold"))
    for change in changes:
        console.print(_change_line(change))
    if not changes:
        console.print(Text("  nothing to merge", style="dim"))
    if package == REFERENCE_PACKAGE:
        console.print(
            Text(
                f"Package name: kept `{REFERENCE_PACKAGE}`. If your package under src/ has another"
                " name, rename it in banned-api and per-file-ignores.",
                style="yellow",
            )
        )
    console.print(Text("Next: install the dev dependencies", style="bold"))
    console.print(f"  {DEV_DEPENDENCIES}")


def _change_line(change: TomlChange) -> Text:
    dotted: str = ".".join(change.keys)
    if change.kind == ChangeKind.ADD:
        return Text(f"  + {dotted}", style="green")
    if change.kind == ChangeKind.APPEND:
        items: str = ", ".join(str(item) for item in _as_list(change.value))
        return Text(f"  + {dotted}: {items}", style="green")
    return Text(
        f"  = kept {dotted} = {change.value} (reference: {change.reference_value})",
        style="yellow",
    )


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []
