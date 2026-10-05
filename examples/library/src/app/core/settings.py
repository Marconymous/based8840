"""Configuration (AGENTS.md §6).

Non-secret values: config/base.toml deep-merged with config/<APP_ENV>.toml -> Settings.
Secrets: environment variables (plus .env locally) -> Secrets.
"""

import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_DIR: Final = Path(__file__).resolve().parents[3]
CONFIG_DIR: Final = PROJECT_DIR / "config"


class DatabaseSettings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    url: str
    echo: bool


class PaginationSettings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    default_page_size: int
    max_page_size: int


class LibrarySettings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    loan_days: int
    export_dir: Path


class NotifierSettings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["log", "file"]
    file_path: Path


class Settings(BaseModel):
    """Non-secret settings. No defaults: the merged TOML must provide every field."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    app_name: str
    log_level: str
    database: DatabaseSettings
    pagination: PaginationSettings
    library: LibrarySettings
    notifier: NotifierSettings


class Secrets(BaseSettings):
    """Secrets, read only from environment variables and the local .env file."""

    model_config = SettingsConfigDict(env_file=PROJECT_DIR / ".env", frozen=True, extra="ignore")

    page_token_secret: SecretStr


class AppConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    settings: Settings
    secrets: Secrets


def deep_merge(base: Mapping[str, object], override: Mapping[str, object]) -> dict[str, object]:
    """Merge two parsed TOML documents; tables merge recursively, other values are replaced."""
    return {
        key: _merge_value(base_value=base.get(key), override_value=override.get(key))
        for key in base.keys() | override.keys()
    }


def _merge_value(*, base_value: object, override_value: object) -> object:
    if override_value is None:
        return base_value
    if isinstance(base_value, dict) and isinstance(override_value, dict):
        return deep_merge(_as_table(base_value), _as_table(override_value))
    return override_value


def _as_table(value: dict[object, object]) -> dict[str, object]:
    # TOML table keys are always strings.
    return {str(key): item for key, item in value.items()}


def _read_toml(path: Path) -> dict[str, object]:
    with path.open("rb") as file:
        return tomllib.load(file)


def load_settings(*, config_dir: Path, app_env: str) -> Settings:
    env_file: Path = config_dir / f"{app_env}.toml"
    if not env_file.is_file():
        raise RuntimeError(f"APP_ENV={app_env!r} but {env_file} does not exist.")
    merged: dict[str, object] = deep_merge(
        _read_toml(config_dir / "base.toml"), _read_toml(env_file)
    )
    return Settings.model_validate(merged)


def load_config(*, config_dir: Path, environ: Mapping[str, str]) -> AppConfig:
    """Build Settings and Secrets once at startup. Crashes if APP_ENV is missing."""
    app_env: str | None = environ.get("APP_ENV")
    if not app_env:
        raise RuntimeError("APP_ENV is required (e.g. APP_ENV=dev). There is no default.")
    settings: Settings = load_settings(config_dir=config_dir, app_env=app_env)
    # pydantic-settings fills the fields from the environment; pyright cannot see that.
    secrets: Secrets = Secrets()  # pyright: ignore[reportCallIssue]
    return AppConfig(settings=settings, secrets=secrets)
