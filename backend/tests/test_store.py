from __future__ import annotations

from pathlib import Path

import pytest
from pyoxigraph import Literal, NamedNode, Quad

from ontoforge.store import graphs
from ontoforge.store.store import GraphStore, ReadOnlyStoreError

EX = "https://example.org/kg/"
ALICE = NamedNode(f"{EX}id/alice")
ACME = NamedNode(f"{EX}id/acme")
WORKS_FOR = NamedNode(f"{EX}ont#worksFor")
LABEL = NamedNode("http://www.w3.org/2000/01/rdf-schema#label")


@pytest.fixture
def store(tmp_path: Path) -> GraphStore:
    with GraphStore.open(tmp_path / "store") as opened:
        yield opened


def _facts() -> list[Quad]:
    return [
        Quad(ALICE, LABEL, Literal("田中太郎", language="ja"), graphs.DATA),
        Quad(ALICE, WORKS_FOR, ACME, graphs.DATA),
        Quad(ACME, LABEL, Literal("株式会社アクメ", language="ja"), graphs.DATA),
    ]


def test_add_and_read_back_quads(store: GraphStore) -> None:
    store.add(_facts())
    assert store.count() == 3
    assert list(store.quads_for_pattern(ALICE, WORKS_FOR, None, graphs.DATA))


def test_named_graphs_stay_separate(store: GraphStore) -> None:
    store.add([Quad(ALICE, LABEL, Literal("a"), graphs.DATA)])
    store.add([Quad(ALICE, LABEL, Literal("a"), graphs.ONTOLOGY)])
    assert store.count(graphs.DATA) == 1
    assert store.count(graphs.ONTOLOGY) == 1
    store.clear_graph(graphs.DATA)
    assert store.count(graphs.DATA) == 0
    assert store.count(graphs.ONTOLOGY) == 1


def test_remove_deletes_only_the_given_quads(store: GraphStore) -> None:
    quads = _facts()
    store.add(quads)
    store.remove([quads[1]])
    assert store.count() == 2


def test_describe_node_returns_the_concise_bounded_description(store: GraphStore) -> None:
    store.add(_facts())
    cbd = store.describe(ALICE)
    subjects = {quad.subject for quad in cbd}
    assert subjects == {ALICE}
    assert len(cbd) == 2


def test_describe_expands_neighbours_when_a_depth_is_given(store: GraphStore) -> None:
    store.add(_facts())
    cbd = store.describe(ALICE, depth=2)
    assert {quad.subject for quad in cbd} == {ALICE, ACME}


def test_describe_of_an_unknown_node_is_empty(store: GraphStore) -> None:
    assert store.describe(NamedNode(f"{EX}id/nobody")) == []


def test_query_runs_sparql(store: GraphStore) -> None:
    store.add(_facts())
    solutions = list(store.query("SELECT ?s WHERE { GRAPH ?g { ?s ?p ?o } }"))
    assert solutions


def test_reopening_the_store_keeps_the_data(tmp_path: Path) -> None:
    path = tmp_path / "store"
    with GraphStore.open(path) as first:
        first.add(_facts())
    with GraphStore.open(path) as second:
        assert second.count() == 3


def test_read_only_handle_can_read(tmp_path: Path) -> None:
    path = tmp_path / "store"
    with GraphStore.open(path) as writable:
        writable.add(_facts())
    with GraphStore.open_read_only(path) as reader:
        assert reader.count() == 3
        assert reader.read_only is True


def test_read_only_handle_refuses_to_add(tmp_path: Path) -> None:
    path = tmp_path / "store"
    with GraphStore.open(path) as writable:
        writable.add(_facts())
    with GraphStore.open_read_only(path) as reader, pytest.raises(ReadOnlyStoreError):
        reader.add(_facts())


def test_read_only_handle_refuses_to_remove_or_clear_or_update(tmp_path: Path) -> None:
    path = tmp_path / "store"
    with GraphStore.open(path) as writable:
        writable.add(_facts())
    with GraphStore.open_read_only(path) as reader:
        with pytest.raises(ReadOnlyStoreError):
            reader.remove(_facts())
        with pytest.raises(ReadOnlyStoreError):
            reader.clear_graph(graphs.DATA)
        with pytest.raises(ReadOnlyStoreError):
            reader.update("CLEAR ALL")


def test_read_only_handle_needs_an_existing_store(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        GraphStore.open_read_only(tmp_path / "absent")


def test_dump_and_load_round_trip(tmp_path: Path, store: GraphStore) -> None:
    store.add(_facts())
    dumped = store.dump_graph(graphs.DATA)
    assert "田中太郎" in dumped
    with GraphStore.open(tmp_path / "other") as other:
        other.load_graph(dumped, graphs.DATA)
        assert other.count(graphs.DATA) == 3


def test_load_skolemises_blank_nodes(tmp_path: Path, store: GraphStore) -> None:
    turtle = f'<{EX}id/alice> <{EX}ont#address> [ <{EX}ont#city> "Tokyo" ] .'
    store.load_graph(turtle, graphs.DATA, skolemize_base=EX)
    assert store.count(graphs.DATA) == 2
    objects = [q.object for q in store.quads_for_pattern(ALICE, None, None, graphs.DATA)]
    assert all(isinstance(term, NamedNode) for term in objects)
    assert f"{EX}.well-known/genid/" in objects[0].value


def test_named_graphs_lists_only_populated_graphs(store: GraphStore) -> None:
    store.add(_facts())
    assert graphs.DATA in set(store.named_graphs())
