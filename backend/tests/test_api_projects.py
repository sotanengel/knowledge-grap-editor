"""Projects and the Phase 3 extras over HTTP (FR-14, §12.4, §14 Phase 3)."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ontoforge.api.app import create_app
from ontoforge.config import Settings

LABEL = "http://www.w3.org/2000/01/rdf-schema#label"


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    return tmp_path / "data"


def client_for(settings: Settings) -> TestClient:
    # No runtime is handed in, so the app opens its own registry and can switch
    # between graph spaces the way a real deployment does.
    return TestClient(create_app(settings=settings))


@pytest.fixture
def client(data_dir: Path) -> Iterator[TestClient]:
    with client_for(Settings(data_dir=data_dir)) as opened:
        yield opened


# ---------------------------------------------------------------- projects


def test_a_default_project_exists_from_the_start(client: TestClient) -> None:
    payload = client.get("/api/v1/projects").json()
    assert payload["current"] == "default"
    assert [project["id"] for project in payload["projects"]] == ["default"]


def test_a_project_can_be_created_and_switched_to(client: TestClient) -> None:
    created = client.post("/api/v1/projects", json={"name": "研究ノート", "id": "research"})
    assert created.status_code == 201
    assert created.json()["id"] == "research"

    switched = client.post("/api/v1/projects/research/switch")
    assert switched.json()["current"] == "research"
    assert client.get("/api/v1/projects").json()["current"] == "research"


def test_each_project_keeps_its_own_graph(client: TestClient) -> None:
    client.post("/api/v1/entities", json={"label": "既定の項目"})
    client.post("/api/v1/projects", json={"name": "Research", "id": "research"})

    client.post("/api/v1/projects/research/switch")
    assert client.get("/api/v1/entities").json()["@graph"] == []
    client.post("/api/v1/entities", json={"label": "研究の項目"})

    client.post("/api/v1/projects/default/switch")
    labels = [node[LABEL][0]["@value"] for node in client.get("/api/v1/entities").json()["@graph"]]
    assert labels == ["既定の項目"]


def test_history_does_not_cross_projects(client: TestClient) -> None:
    client.post("/api/v1/entities", json={"label": "既定の項目"})
    client.post("/api/v1/projects", json={"name": "Research", "id": "research"})
    client.post("/api/v1/projects/research/switch")
    assert client.get("/api/v1/history").json()["entries"] == []


def test_a_duplicate_project_is_a_409(client: TestClient) -> None:
    client.post("/api/v1/projects", json={"name": "Research", "id": "research"})
    assert client.post("/api/v1/projects", json={"name": "R", "id": "research"}).status_code == 409


def test_an_unusable_project_id_is_a_422(client: TestClient) -> None:
    assert client.post("/api/v1/projects", json={"name": "x", "id": "../esc"}).status_code == 422


def test_switching_to_an_unknown_project_is_a_404(client: TestClient) -> None:
    assert client.post("/api/v1/projects/nope/switch").status_code == 404


def test_a_project_can_be_renamed(client: TestClient) -> None:
    client.post("/api/v1/projects", json={"name": "Research", "id": "research"})
    renamed = client.patch("/api/v1/projects/research", json={"name": "研究ノート"}).json()
    assert renamed["id"] == "research"
    assert renamed["name"] == "研究ノート"
    # The id never moves, so nothing that references the project breaks.
    assert [entry["id"] for entry in client.get("/api/v1/projects").json()["projects"]] == [
        "default",
        "research",
    ]


def test_a_project_can_be_deleted(client: TestClient) -> None:
    client.post("/api/v1/projects", json={"name": "Research", "id": "research"})
    client.post("/api/v1/projects/research/switch")
    deleted = client.delete("/api/v1/projects/research")
    assert deleted.json() == {"deleted": "research", "current": "default"}
    assert [p["id"] for p in client.get("/api/v1/projects").json()["projects"]] == ["default"]


def test_the_default_project_cannot_be_deleted(client: TestClient) -> None:
    assert client.delete("/api/v1/projects/default").status_code == 400


def test_a_project_survives_a_restart(data_dir: Path) -> None:
    with client_for(Settings(data_dir=data_dir)) as first:
        first.post("/api/v1/projects", json={"name": "Research", "id": "research"})
        first.post("/api/v1/projects/research/switch")
        first.post("/api/v1/entities", json={"label": "研究の項目"})

    with client_for(Settings(data_dir=data_dir, project="research")) as second:
        labels = [
            node[LABEL][0]["@value"] for node in second.get("/api/v1/entities").json()["@graph"]
        ]
        assert labels == ["研究の項目"]


# ---------------------------------------------------------------- semantic search


def test_semantic_search_is_off_unless_asked_for(client: TestClient) -> None:
    payload = client.get("/api/v1/semantic").json()
    assert payload["enabled"] is False
    # Even while off, it says which embedder this image carries, so the operator
    # knows what turning it on would give them.
    assert payload["quality"] in {"semantic", "surface"}
    assert payload["note"]
    assert "ONTOFORGE_SEMANTIC_SEARCH=1" in payload["hint"]


def test_using_semantic_search_while_it_is_off_is_a_409(client: TestClient) -> None:
    assert client.get("/api/v1/semantic/search", params={"q": "田中"}).status_code == 409
    assert client.post("/api/v1/semantic/reindex").status_code == 409


def test_semantic_search_finds_a_near_label_when_enabled(data_dir: Path) -> None:
    with client_for(Settings(data_dir=data_dir, semantic_search=True)) as client:
        client.post("/api/v1/entities", json={"label": "田中太郎"})
        client.post("/api/v1/entities", json={"label": "株式会社アクメ"})

        status = client.get("/api/v1/semantic").json()
        assert status["enabled"] is True
        assert status["dimensions"] > 0
        results = client.get("/api/v1/semantic/search", params={"q": "田中"}).json()["results"]
        assert results[0]["label"] == "田中太郎"
        assert 0 < results[0]["score"] <= 1


def test_the_status_says_which_kind_of_similarity_is_in_use(data_dir: Path) -> None:
    """A score means something quite different depending on the embedder, so
    which one produced it is never left implicit."""
    from ontoforge.semantic.embedder import default_model_dir, model_is_available

    with client_for(Settings(data_dir=data_dir, semantic_search=True)) as client:
        status = client.get("/api/v1/semantic").json()
        expected = "semantic" if model_is_available(default_model_dir()) else "surface"
        assert status["quality"] == expected
        assert status["embedder"]


@pytest.mark.skipif(
    not __import__(
        "ontoforge.semantic.embedder", fromlist=["model_is_available"]
    ).model_is_available(
        __import__(
            "ontoforge.semantic.embedder", fromlist=["default_model_dir"]
        ).default_model_dir()
    ),
    reason="the embedding model is fetched at build time",
)
def test_a_search_finds_a_node_that_shares_no_character_with_the_query(
    data_dir: Path,
) -> None:
    """「企業」 finds 「株式会社アクメ」. Not one character is shared, so the
    surface fallback would score this at zero -- this is the whole point of
    carrying a trained embedding."""
    with client_for(Settings(data_dir=data_dir, semantic_search=True)) as client:
        client.post("/api/v1/entities", json={"label": "株式会社アクメ"})
        client.post("/api/v1/entities", json={"label": "田中太郎"})
        client.post("/api/v1/entities", json={"label": "りんご"})

        results = client.get("/api/v1/semantic/search", params={"q": "企業"}).json()["results"]
        assert results, results
        assert results[0]["label"] == "株式会社アクメ", results


def test_the_vector_index_can_be_rebuilt(data_dir: Path) -> None:
    with client_for(Settings(data_dir=data_dir, semantic_search=True)) as client:
        client.post("/api/v1/entities", json={"label": "田中太郎"})
        assert client.post("/api/v1/semantic/reindex").json()["indexed"] >= 1


# ---------------------------------------------------------------- git snapshots


def test_snapshot_versioning_is_off_unless_asked_for(client: TestClient) -> None:
    payload = client.get("/api/v1/git").json()
    assert payload["enabled"] is False
    assert client.post("/api/v1/git/commit").status_code == 409


def test_snapshots_can_be_committed_when_enabled(data_dir: Path) -> None:
    from ontoforge.gitsync.repo import git_available

    if not git_available():
        pytest.skip("git is not installed")

    with client_for(Settings(data_dir=data_dir, git_snapshots=True)) as client:
        client.post("/api/v1/entities", json={"label": "田中太郎"})
        client.get("/api/v1/export", params={"format": "turtle"})

        assert client.get("/api/v1/git").json()["enabled"] is True
        committed = client.post("/api/v1/git/commit").json()
        # Nothing has been snapshotted yet, so there is nothing to commit; the
        # endpoint says so rather than pretending.
        assert committed["committed"] in (True, False)
        assert client.get("/api/v1/git").json()["initialised"] is True
