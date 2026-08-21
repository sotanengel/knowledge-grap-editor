from __future__ import annotations

from pathlib import Path

import pytest
from pyoxigraph import Literal, NamedNode, Quad

from ontoforge.changelog.log import ChangeLog
from ontoforge.changelog.snapshot import SnapshotPolicy, SnapshotStore, restore
from ontoforge.store import graphs
from ontoforge.store.store import GraphStore

ALICE = NamedNode("https://example.org/kg/id/alice")
LABEL = NamedNode("http://www.w3.org/2000/01/rdf-schema#label")


def _quad(text: str) -> Quad:
    return Quad(ALICE, LABEL, Literal(text, language="ja"), graphs.DATA)


@pytest.fixture
def store(tmp_path: Path) -> GraphStore:
    with GraphStore.open(tmp_path / "store") as opened:
        yield opened


@pytest.fixture
def snapshots(tmp_path: Path) -> SnapshotStore:
    return SnapshotStore(tmp_path / "snapshots")


def test_writing_a_snapshot_produces_a_trig_file(
    snapshots: SnapshotStore, store: GraphStore
) -> None:
    store.add([_quad("a")])
    written = snapshots.write(store, seq=1)
    assert written.path.suffix == ".trig"
    assert written.seq == 1
    assert written.path.read_text(encoding="utf-8")


def test_latest_returns_the_highest_sequence(snapshots: SnapshotStore, store: GraphStore) -> None:
    store.add([_quad("a")])
    snapshots.write(store, seq=1)
    snapshots.write(store, seq=9)
    snapshots.write(store, seq=4)
    latest = snapshots.latest()
    assert latest is not None
    assert latest.seq == 9


def test_latest_is_none_when_no_snapshot_exists(snapshots: SnapshotStore) -> None:
    assert snapshots.latest() is None


def test_a_snapshot_is_a_standalone_portable_dump(
    tmp_path: Path, snapshots: SnapshotStore, store: GraphStore
) -> None:
    store.add([_quad("a"), Quad(ALICE, LABEL, Literal("t"), graphs.ONTOLOGY)])
    written = snapshots.write(store, seq=1)
    with GraphStore.open(tmp_path / "restored") as fresh:
        fresh.load_dataset(written.path.read_text(encoding="utf-8"))
        assert fresh.count(graphs.DATA) == 1
        assert fresh.count(graphs.ONTOLOGY) == 1


def test_restore_replays_patches_recorded_after_the_snapshot(tmp_path: Path) -> None:
    source = tmp_path / "source"
    log = ChangeLog(tmp_path / "changelog")
    snapshots = SnapshotStore(tmp_path / "snapshots")
    with GraphStore.open(source) as store:
        log.apply(store, additions=[_quad("a")], actor="user")
        snapshots.write(store, seq=log.last_seq)
        log.apply(store, additions=[_quad("b")], actor="user")
        log.apply(store, additions=[_quad("c")], actor="user")

    with GraphStore.open(tmp_path / "rebuilt") as rebuilt:
        result = restore(rebuilt, snapshots=snapshots, changelog=log)
        assert result.from_seq == 1
        assert result.replayed == 2
        assert rebuilt.count(graphs.DATA) == 3


def test_restore_without_a_snapshot_replays_the_whole_log(tmp_path: Path) -> None:
    log = ChangeLog(tmp_path / "changelog")
    snapshots = SnapshotStore(tmp_path / "snapshots")
    with GraphStore.open(tmp_path / "source") as store:
        log.apply(store, additions=[_quad("a")], actor="user")
        log.apply(store, additions=[_quad("b")], actor="user")

    with GraphStore.open(tmp_path / "rebuilt") as rebuilt:
        result = restore(rebuilt, snapshots=snapshots, changelog=log)
        assert result.from_seq == 0
        assert result.replayed == 2
        assert rebuilt.count(graphs.DATA) == 2


def test_restore_honours_a_target_sequence(tmp_path: Path) -> None:
    log = ChangeLog(tmp_path / "changelog")
    snapshots = SnapshotStore(tmp_path / "snapshots")
    with GraphStore.open(tmp_path / "source") as store:
        for text in "abc":
            log.apply(store, additions=[_quad(text)], actor="user")

    with GraphStore.open(tmp_path / "rebuilt") as rebuilt:
        restore(rebuilt, snapshots=snapshots, changelog=log, upto_seq=2)
        assert rebuilt.count(graphs.DATA) == 2


def test_restore_replays_deletions_too(tmp_path: Path) -> None:
    log = ChangeLog(tmp_path / "changelog")
    snapshots = SnapshotStore(tmp_path / "snapshots")
    with GraphStore.open(tmp_path / "source") as store:
        log.apply(store, additions=[_quad("a"), _quad("b")], actor="user")
        log.apply(store, deletions=[_quad("a")], actor="user")

    with GraphStore.open(tmp_path / "rebuilt") as rebuilt:
        restore(rebuilt, snapshots=snapshots, changelog=log)
        assert rebuilt.count(graphs.DATA) == 1


def test_the_policy_fires_every_n_operations() -> None:
    policy = SnapshotPolicy(every_ops=3, every_seconds=None)
    assert [policy.should_snapshot(seq=n, now=0.0) for n in range(1, 7)] == [
        False,
        False,
        True,
        False,
        False,
        True,
    ]


def test_the_policy_fires_after_the_configured_interval() -> None:
    policy = SnapshotPolicy(every_ops=None, every_seconds=60)
    assert policy.should_snapshot(seq=1, now=0.0) is False
    assert policy.should_snapshot(seq=2, now=61.0) is True
    assert policy.should_snapshot(seq=3, now=70.0) is False


def test_a_disabled_policy_never_fires() -> None:
    policy = SnapshotPolicy(every_ops=None, every_seconds=None)
    assert policy.should_snapshot(seq=100, now=1e9) is False


def test_pruning_keeps_only_the_most_recent_snapshots(
    snapshots: SnapshotStore, store: GraphStore
) -> None:
    store.add([_quad("a")])
    for seq in range(1, 6):
        snapshots.write(store, seq=seq)
    snapshots.prune(keep=2)
    assert [snapshot.seq for snapshot in snapshots.all()] == [4, 5]
