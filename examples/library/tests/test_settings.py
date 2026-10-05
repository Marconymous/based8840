"""Tests for config loading."""

from pathlib import Path

import pytest

from app.core.settings import CONFIG_DIR, Settings, deep_merge, load_config, load_settings


def test_load_config_requires_app_env() -> None:
    with pytest.raises(RuntimeError, match="APP_ENV is required"):
        _ = load_config(config_dir=CONFIG_DIR, environ={})


def test_load_settings_rejects_unknown_env() -> None:
    with pytest.raises(RuntimeError, match="does not exist"):
        _ = load_settings(config_dir=CONFIG_DIR, app_env="staging")


def test_env_file_overrides_base() -> None:
    settings: Settings = load_settings(config_dir=CONFIG_DIR, app_env="test")

    assert settings.app_name == "library"  # from base.toml
    assert settings.pagination.default_page_size == 2  # from test.toml
    assert settings.notifier.kind == "log"  # base.toml value kept inside a merged table


@pytest.mark.parametrize("app_env", ["dev", "test", "prod"])
def test_every_environment_is_complete(app_env: str) -> None:
    settings: Settings = load_settings(config_dir=CONFIG_DIR, app_env=app_env)

    assert settings.app_name


def test_settings_have_no_defaults(tmp_path: Path) -> None:
    _ = (tmp_path / "base.toml").write_text('app_name = "library"\n')
    _ = (tmp_path / "test.toml").write_text("")

    with pytest.raises(ValueError, match="log_level"):
        _ = load_settings(config_dir=tmp_path, app_env="test")


@pytest.mark.parametrize(
    ("base", "override", "expected"),
    [
        ({"a": 1}, {"a": 2}, {"a": 2}),
        ({"a": 1}, {"b": 2}, {"a": 1, "b": 2}),
        ({"t": {"x": 1, "y": 2}}, {"t": {"y": 3}}, {"t": {"x": 1, "y": 3}}),
    ],
)
def test_deep_merge(
    base: dict[str, object], override: dict[str, object], expected: dict[str, object]
) -> None:
    assert deep_merge(base, override) == expected


@pytest.mark.parametrize(
    ("app_env", "debug_errors", "log_format"),
    [("dev", True, "text"), ("test", True, "text"), ("prod", False, "json")],
)
def test_environment_driven_behavior(app_env: str, debug_errors: bool, log_format: str) -> None:
    settings: Settings = load_settings(config_dir=CONFIG_DIR, app_env=app_env)

    assert settings.debug_errors is debug_errors
    assert settings.log_format == log_format
