from __future__ import annotations

from pathlib import Path

import pytest
from pyoxigraph import Literal, NamedNode, Quad

from ontoforge.changelog.log import ChangeLog
from ontoforge.store import graphs
from ontoforge.store.store import GraphStore

ALICE = NamedNode("https://example.org/kg/id/alice")
LABEL = NamedNode("http://www.w3.org/2000/01/rdf-schema#label")


@pytest.fixture
def store(tmp_path: Path) -> GraphStore:
    with GraphStore.open(tmp_path / "store") as opened:
        yield opened


@pytest.fixture
def log(tmp_path: Path) -> ChangeLog:
    return ChangeLog(tmp_path / "changelog")


def _quad(text: str) -> Quad:
    return Quad(ALICE, LABEL, Literal(text, language="ja"), graphs.DATA)


def test_sequence_numbers_start_at_one_and_increase(log: ChangeLog, store: GraphStore) -> None:
    first = log.apply(store, additions=[_quad("a")], actor="user")
    second = log.apply(store, additions=[_quad("b")], actor="user")
    assert (first.seq, second.seq) == (1, 2)


def test_apply_writes_through_to_the_store(log: ChangeLog, store: GraphStore) -> None:
    log.apply(store, additions=[_quad("a")], actor="user")
    assert store.count(graphs.DATA) == 1


def test_the_actor_is_recorded(log: ChangeLog, store: GraphStore) -> None:
    log.apply(store, additions=[_quad("a")], actor="import:people.ttl")
    assert log.read_all()[0].actor == "import:people.ttl"


def test_an_empty_change_is_not_recorded(log: ChangeLog, store: GraphStore) -> None:
    assert log.apply(store, additions=[], deletions=[], actor="user") is None
    assert log.read_all() == []


def test_the_log_survives_a_reopen(tmp_path: Path, store: GraphStore) -> None:
    first = ChangeLog(tmp_path / "changelog")
    first.apply(store, additions=[_quad("a")], actor="user")
    second = ChangeLog(tmp_path / "changelog")
    assert len(second.read_all()) == 1
    assert second.apply(store, additions=[_quad("b")], actor="user").seq == 2


def test_undo_appends_an_inverse_patch_rather_than_rewriting(
    log: ChangeLog, store: GraphStore
) -> None:
    log.apply(store, additions=[_quad("a")], actor="user")
    undone = log.undo(store)
    assert undone is not None
    assert store.count(graphs.DATA) == 0
    assert [patch.seq for patch in log.read_all()] == [1, 2]


def test_redo_restores_the_undone_change(log: ChangeLog, store: GraphStore) -> None:
    log.apply(store, additions=[_quad("a")], actor="user")
    log.undo(store)
    assert log.redo(store) is not None
    assert store.count(graphs.DATA) == 1


def test_undo_and_redo_are_no_ops_when_there_is_nothing_to_do(
    log: ChangeLog, store: GraphStore
) -> None:
    assert log.undo(store) is None
    log.apply(store, additions=[_quad("a")], actor="user")
    assert log.redo(store) is None


def test_a_new_change_clears_the_redo_stack(log: ChangeLog, store: GraphStore) -> None:
    log.apply(store, additions=[_quad("a")], actor="user")
    log.undo(store)
    log.apply(store, additions=[_quad("b")], actor="user")
    assert log.redo(store) is None


def test_undo_walks_back_through_several_changes(log: ChangeLog, store: GraphStore) -> None:
    log.apply(store, additions=[_quad("a")], actor="user")
    log.apply(store, additions=[_quad("b")], actor="user")
    log.undo(store)
    log.undo(store)
    assert store.count(graphs.DATA) == 0


def test_history_is_returned_newest_first_and_can_be_limited(
    log: ChangeLog, store: GraphStore
) -> None:
    for text in "abc":
        log.apply(store, additions=[_quad(text)], actor="user")
    assert [patch.seq for patch in log.history(limit=2)] == [3, 2]
