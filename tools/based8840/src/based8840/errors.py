"""Exceptions the CLI turns into a usage error (exit code 2)."""


class Based8840Error(Exception):
    """Base for every error the CLI reports without a stack trace."""


class ProjectNotFoundError(Based8840Error):
    """No `pyproject.toml` with a `[project]` table in the directory or its parents."""


class PackageNotFoundError(Based8840Error):
    """Layer checks need exactly one package under `src/`."""


class ToolNotFoundError(Based8840Error):
    """An external command (usually `uv`) is not installed."""
