from __future__ import annotations

from pathlib import Path

import pytest

from ontoforge.projects.store import (
    DEFAULT_PROJECT,
    PROJECT_DIRS,
    ProjectExistsError,
    ProjectNotFoundError,
    ProjectStore,
    slugify,
)


@pytest.fixture
def projects(tmp_path: Path) -> ProjectStore:
    return ProjectStore(tmp_path / "data")


def test_a_new_project_gets_its_own_complete_layout(projects: ProjectStore) -> None:
    project = projects.create(name="研究ノート")
    for directory in PROJECT_DIRS:
        assert (project.path / directory).is_dir()


def test_the_id_is_derived_from_the_name(projects: ProjectStore) -> None:
    assert projects.create(name="Research Notes").id == "research-notes"


def test_a_name_with_no_usable_characters_still_gets_an_id(projects: ProjectStore) -> None:
    assert projects.create(name="研究").id == "project"


def test_an_explicit_id_is_honoured(projects: ProjectStore) -> None:
    assert projects.create(name="Research", project_id="kg-2026").id == "kg-2026"


def test_a_duplicate_id_is_refused(projects: ProjectStore) -> None:
    projects.create(name="Research")
    with pytest.raises(ProjectExistsError):
        projects.create(name="Research")


def test_an_empty_name_is_refused(projects: ProjectStore) -> None:
    with pytest.raises(ValueError, match="name"):
        projects.create(name="   ")


@pytest.mark.parametrize("bad", ["../escape", "/absolute", "UPPER", "with space", "a" * 65])
def test_an_id_may_not_escape_the_projects_directory(projects: ProjectStore, bad: str) -> None:
    with pytest.raises(ValueError, match="project id"):
        projects.create(name="x", project_id=bad)


def test_a_blank_id_means_derive_it_from_the_name(projects: ProjectStore) -> None:
    assert projects.create(name="Research Notes", project_id="  ").id == "research-notes"


def test_projects_are_listed_with_the_default_first(projects: ProjectStore) -> None:
    projects.create(name="Zebra")
    projects.ensure_default()
    projects.create(name="Alpha")
    assert [project.id for project in projects.all()] == ["default", "alpha", "zebra"]


def test_an_unknown_project_is_reported(projects: ProjectStore) -> None:
    with pytest.raises(ProjectNotFoundError):
        projects.get("nope")


def test_a_project_can_be_renamed_without_moving_its_data(projects: ProjectStore) -> None:
    created = projects.create(name="Research")
    (created.path / "store" / "marker").write_text("x", encoding="utf-8")
    renamed = projects.rename(created.id, "研究ノート")
    assert renamed.id == created.id
    assert renamed.name == "研究ノート"
    assert (created.path / "store" / "marker").is_file()


def test_deleting_removes_the_whole_project(projects: ProjectStore) -> None:
    created = projects.create(name="Research")
    projects.delete(created.id)
    assert not created.path.exists()
    assert projects.all() == []


def test_the_default_project_cannot_be_deleted(projects: ProjectStore) -> None:
    projects.ensure_default()
    with pytest.raises(ValueError, match="default"):
        projects.delete(DEFAULT_PROJECT)


def test_ensure_default_is_idempotent(projects: ProjectStore) -> None:
    first = projects.ensure_default()
    assert projects.ensure_default().created_at == first.created_at


# ---------------------------------------------------------------- migration


def test_an_existing_single_graph_becomes_the_default_project(tmp_path: Path) -> None:
    data = tmp_path / "data"
    for directory in PROJECT_DIRS:
        (data / directory).mkdir(parents=True)
    (data / "store" / "CURRENT").write_text("rocksdb", encoding="utf-8")
    (data / "changelog" / "patches.rdfp").write_text('H id "1" .\n', encoding="utf-8")

    projects = ProjectStore(data)
    default = projects.ensure_default()

    assert (default.path / "store" / "CURRENT").read_text(encoding="utf-8") == "rocksdb"
    assert (default.path / "changelog" / "patches.rdfp").is_file()
    # The old locations are gone, so nothing reads them by accident.
    assert not (data / "store").exists()


def test_migration_does_not_clobber_a_default_project_that_already_has_data(
    tmp_path: Path,
) -> None:
    data = tmp_path / "data"
    (data / "store").mkdir(parents=True)
    (data / "store" / "CURRENT").write_text("legacy", encoding="utf-8")

    projects = ProjectStore(data)
    existing = projects.create(name="デフォルト", project_id=DEFAULT_PROJECT)
    (existing.path / "store" / "CURRENT").write_text("current", encoding="utf-8")

    projects.ensure_default()
    assert (existing.path / "store" / "CURRENT").read_text(encoding="utf-8") == "current"


def test_an_empty_legacy_directory_is_cleared_away(tmp_path: Path) -> None:
    data = tmp_path / "data"
    (data / "store").mkdir(parents=True)
    (data / "snapshots").mkdir()

    projects = ProjectStore(data)
    default = projects.ensure_default()

    assert (default.path / "store").is_dir()
    # Nothing is left at the old locations to suggest two live layouts.
    assert not (data / "store").exists()
    assert not (data / "snapshots").exists()


def test_slugify_leaves_something_usable() -> None:
    assert slugify("My Project!") == "my-project"
    assert slugify("  ---  ") == "project"
    assert len(slugify("x" * 200)) == 64


# ---------------------------------------------------------------- the registry


def test_each_project_gets_its_own_graph(tmp_path: Path) -> None:
    from pyoxigraph import Literal, NamedNode, Quad

    from ontoforge.config import Settings
    from ontoforge.namespaces import RDFS_LABEL
    from ontoforge.projects.registry import ProjectRegistry
    from ontoforge.store import graphs

    settings = Settings(data_dir=tmp_path / "data")
    with ProjectRegistry(settings) as registry:
        registry.projects.create(name="Research", project_id="research")

        default = registry.current
        default.write(
            additions=[Quad(NamedNode("https://a"), RDFS_LABEL, Literal("既定の項目"), graphs.DATA)]
        )

        other = registry.switch("research")
        assert other.store.count() == 0
        assert other.search.search("既定") == []

        other.write(
            additions=[Quad(NamedNode("https://b"), RDFS_LABEL, Literal("研究の項目"), graphs.DATA)]
        )
        assert registry.switch("default").store.count() == 1


def test_undo_history_does_not_cross_projects(tmp_path: Path) -> None:
    from pyoxigraph import Literal, NamedNode, Quad

    from ontoforge.config import Settings
    from ontoforge.namespaces import RDFS_LABEL
    from ontoforge.projects.registry import ProjectRegistry
    from ontoforge.store import graphs

    with ProjectRegistry(Settings(data_dir=tmp_path / "data")) as registry:
        registry.projects.create(name="Research", project_id="research")
        registry.current.write(
            additions=[Quad(NamedNode("https://a"), RDFS_LABEL, Literal("x"), graphs.DATA)]
        )
        assert registry.switch("research").changelog.can_undo is False
        assert registry.switch("default").changelog.can_undo is True


def test_switching_to_an_unknown_project_is_refused(tmp_path: Path) -> None:
    from ontoforge.config import Settings
    from ontoforge.projects.registry import ProjectRegistry

    with (
        ProjectRegistry(Settings(data_dir=tmp_path / "data")) as registry,
        pytest.raises(ProjectNotFoundError),
    ):
        registry.switch("nope")


def test_the_same_runtime_is_reused_for_a_project(tmp_path: Path) -> None:
    from ontoforge.config import Settings
    from ontoforge.projects.registry import ProjectRegistry

    with ProjectRegistry(Settings(data_dir=tmp_path / "data")) as registry:
        assert registry.open("default") is registry.open("default")


def test_deleting_the_open_project_falls_back_to_the_default(tmp_path: Path) -> None:
    from ontoforge.config import Settings
    from ontoforge.projects.registry import ProjectRegistry

    with ProjectRegistry(Settings(data_dir=tmp_path / "data")) as registry:
        registry.projects.create(name="Research", project_id="research")
        registry.switch("research")
        registry.delete("research")
        assert registry.current_id == DEFAULT_PROJECT


def test_a_configured_project_that_does_not_exist_falls_back(tmp_path: Path) -> None:
    from ontoforge.config import Settings
    from ontoforge.projects.registry import ProjectRegistry

    settings = Settings(data_dir=tmp_path / "data", project="absent")
    with ProjectRegistry(settings) as registry:
        assert registry.current_id == DEFAULT_PROJECT
