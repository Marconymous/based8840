"""Exceptions the CLI turns into a usage error (exit code 2)."""


class Based8840Error(Exception):
    """Base for every error the CLI reports without a stack trace."""


class ProjectNotFoundError(Based8840Error):
    """No `pyproject.toml` with a `[project]` table in the directory or its parents."""


class PackageNotFoundError(Based8840Error):
    """Layer checks need exactly one package under `src/`."""


class ToolNotFoundError(Based8840Error):
    """An external command (usually `uv`) is not installed."""


class InitConflictError(Based8840Error):
    """`init` would overwrite files that already exist in the target project."""


class ChangedFilesError(Based8840Error):
    """`git` could not list the files changed against the given branch."""


class RuleNotFoundError(Based8840Error):
    """`explain` got a code that no check reports."""


class AtlasEnvError(Based8840Error):
    """`--atlas-env` is missing, or given where no Atlas check can run."""
