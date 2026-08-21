"""Runtime configuration.

Values are resolved from three sources, most significant first: ``ONTOFORGE_*``
environment variables, ``<data_dir>/config.yaml``, then the defaults given in
the system definition (§12.3).
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

ENV_PREFIX = "ONTOFORGE_"
CONFIG_FILENAME = "config.yaml"
DEFAULT_DATA_DIR = "/data"
DEFAULT_BASE_IRI = "https://example.org/kg/"

ReasonerProfile = Literal["none", "rdfs", "rl-lite"]


class Settings(BaseModel):
    """The full runtime configuration of a single OntoForge instance."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    base_iri: str = DEFAULT_BASE_IRI
    data_dir: Path = Path(DEFAULT_DATA_DIR)
    auth_token: str | None = None
    reasoner: ReasonerProfile = "rdfs"
    reasoner_max_iter: int = Field(default=20, ge=1)
    query_timeout_ms: int = Field(default=10_000, ge=1)

    @field_validator("base_iri")
    @classmethod
    def _ensure_trailing_separator(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("base_iri must not be empty")
        return value if value.endswith(("/", "#")) else f"{value}/"

    @field_validator("auth_token")
    @classmethod
    def _blank_token_means_no_auth(cls, value: str | None) -> str | None:
        return value or None

    @property
    def store_dir(self) -> Path:
        return self.data_dir / "store"

    @property
    def snapshots_dir(self) -> Path:
        return self.data_dir / "snapshots"

    @property
    def changelog_dir(self) -> Path:
        return self.data_dir / "changelog"

    @property
    def index_dir(self) -> Path:
        return self.data_dir / "index"

    @property
    def config_file(self) -> Path:
        return self.data_dir / CONFIG_FILENAME

    @property
    def auth_required(self) -> bool:
        return self.auth_token is not None

    def ensure_directories(self) -> None:
        """Create the ``/data`` layout described in §5.1 if it is not there yet."""
        for directory in (
            self.data_dir,
            self.store_dir,
            self.snapshots_dir,
            self.changelog_dir,
            self.index_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)


def _read_config_file(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:  # pragma: no cover - message varies by input
        raise ValueError(f"{path} is not valid YAML: {error}") from error
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValueError(f"{path} must contain a mapping, got {type(raw).__name__}")
    return raw


def load_settings(
    *,
    data_dir: Path | str | None = None,
    env: Mapping[str, str] | None = None,
) -> Settings:
    """Build :class:`Settings` from the config file and the environment."""
    environment = os.environ if env is None else env

    if data_dir is not None:
        resolved_data_dir = Path(data_dir)
    else:
        resolved_data_dir = Path(environment.get(f"{ENV_PREFIX}DATA_DIR", DEFAULT_DATA_DIR))

    values = _read_config_file(resolved_data_dir / CONFIG_FILENAME)
    unknown = set(values) - set(Settings.model_fields)
    if unknown:
        raise ValueError(f"unknown configuration keys: {', '.join(sorted(unknown))}")

    for field in Settings.model_fields:
        env_value = environment.get(f"{ENV_PREFIX}{field.upper()}")
        if env_value is not None:
            values[field] = env_value

    values["data_dir"] = resolved_data_dir
    return Settings(**values)
