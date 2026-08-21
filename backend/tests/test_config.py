from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from ontoforge.config import CONFIG_FILENAME, DEFAULT_DATA_DIR, Settings, load_settings


def test_defaults_match_the_specification() -> None:
    settings = Settings()
    assert settings.base_iri == "https://example.org/kg/"
    assert settings.data_dir == Path(DEFAULT_DATA_DIR)
    assert settings.auth_token is None
    assert settings.reasoner == "rdfs"
    assert settings.reasoner_max_iter == 20
    assert settings.query_timeout_ms == 10_000


def test_base_iri_is_normalised_to_end_with_a_separator() -> None:
    assert Settings(base_iri="https://example.org/kg").base_iri == "https://example.org/kg/"


def test_derived_directories_live_under_the_open_project(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path)
    project = tmp_path / "projects" / "default"
    assert settings.project == "default"
    assert settings.store_dir == project / "store"
    assert settings.snapshots_dir == project / "snapshots"
    assert settings.changelog_dir == project / "changelog"
    assert settings.index_dir == project / "index"
    # The config file is shared: it configures the installation, not a project.
    assert settings.config_file == tmp_path / CONFIG_FILENAME


def test_switching_project_moves_every_directory(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path).for_project("research")
    assert settings.store_dir == tmp_path / "projects" / "research" / "store"
    assert settings.base_iri == "https://example.org/kg/"


def test_the_phase_three_features_are_off_unless_asked_for() -> None:
    settings = Settings()
    assert settings.semantic_search is False
    assert settings.git_snapshots is False
    assert settings.git_remote is None


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1", True),
        ("true", True),
        ("TRUE", True),
        ("yes", True),
        ("on", True),
        ("0", False),
        ("false", False),
        ("", False),
        ("nonsense", False),
    ],
)
def test_boolean_environment_variables_read_the_usual_spellings(
    tmp_path: Path, raw: str, expected: bool
) -> None:
    settings = load_settings(data_dir=tmp_path, env={"ONTOFORGE_SEMANTIC_SEARCH": raw})
    assert settings.semantic_search is expected


def test_ensure_directories_creates_the_whole_layout(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path / "data")
    settings.ensure_directories()
    for directory in (
        settings.store_dir,
        settings.snapshots_dir,
        settings.changelog_dir,
        settings.index_dir,
    ):
        assert directory.is_dir()


def test_unknown_reasoner_profile_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(reasoner="owl-dl")


def test_load_settings_reads_the_config_file(tmp_path: Path) -> None:
    tmp_path.mkdir(exist_ok=True)
    (tmp_path / CONFIG_FILENAME).write_text(
        "base_iri: https://acme.example/kg/\nquery_timeout_ms: 500\n", encoding="utf-8"
    )
    settings = load_settings(data_dir=tmp_path, env={})
    assert settings.base_iri == "https://acme.example/kg/"
    assert settings.query_timeout_ms == 500


def test_environment_variables_win_over_the_config_file(tmp_path: Path) -> None:
    (tmp_path / CONFIG_FILENAME).write_text("query_timeout_ms: 500\n", encoding="utf-8")
    settings = load_settings(
        data_dir=tmp_path, env={"ONTOFORGE_QUERY_TIMEOUT_MS": "1234", "ONTOFORGE_REASONER": "none"}
    )
    assert settings.query_timeout_ms == 1234
    assert settings.reasoner == "none"


def test_load_settings_resolves_the_data_dir_from_the_environment(tmp_path: Path) -> None:
    settings = load_settings(env={"ONTOFORGE_DATA_DIR": str(tmp_path)})
    assert settings.data_dir == tmp_path


def test_load_settings_tolerates_a_missing_config_file(tmp_path: Path) -> None:
    settings = load_settings(data_dir=tmp_path / "absent", env={})
    assert settings.base_iri == "https://example.org/kg/"


def test_load_settings_rejects_a_malformed_config_file(tmp_path: Path) -> None:
    (tmp_path / CONFIG_FILENAME).write_text("- just\n- a\n- list\n", encoding="utf-8")
    with pytest.raises(ValueError, match="mapping"):
        load_settings(data_dir=tmp_path, env={})
