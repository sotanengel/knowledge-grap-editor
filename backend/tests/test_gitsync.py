from __future__ import annotations

from pathlib import Path

import pytest

from ontoforge.gitsync.repo import GitError, SnapshotRepository, commit_message, git_available

pytestmark = pytest.mark.skipif(not git_available(), reason="git is not installed")


@pytest.fixture
def repository(tmp_path: Path) -> SnapshotRepository:
    return SnapshotRepository(tmp_path / "snapshots")


def _snapshot(repository: SnapshotRepository, name: str, body: str = "<a> <b> <c> .") -> Path:
    repository.directory.mkdir(parents=True, exist_ok=True)
    path = repository.directory / name
    path.write_text(body, encoding="utf-8")
    return path


def test_a_fresh_directory_is_not_a_repository_yet(repository: SnapshotRepository) -> None:
    assert not repository.initialised
    assert repository.status() == []
    assert repository.log() == []


def test_initialising_is_idempotent(repository: SnapshotRepository) -> None:
    repository.initialise()
    repository.initialise()
    assert repository.initialised


def test_a_snapshot_is_committed(repository: SnapshotRepository) -> None:
    _snapshot(repository, "snapshot-000000000001.trig")
    result = repository.commit(commit_message(1))
    assert result.committed
    assert result.revision
    assert result.files >= 1


def test_committing_with_nothing_changed_does_nothing(repository: SnapshotRepository) -> None:
    _snapshot(repository, "snapshot-000000000001.trig")
    repository.commit(commit_message(1))
    second = repository.commit(commit_message(2))
    assert not second.committed
    assert second.revision is None


def test_each_snapshot_becomes_its_own_commit(repository: SnapshotRepository) -> None:
    for seq in (1, 2, 3):
        _snapshot(repository, f"snapshot-{seq:012d}.trig", f"<a> <b> <c{seq}> .")
        repository.commit(commit_message(seq))
    subjects = [entry["subject"] for entry in repository.log()]
    assert subjects == [commit_message(3), commit_message(2), commit_message(1)]


def test_the_commit_says_which_change_it_captured(repository: SnapshotRepository) -> None:
    assert commit_message(7, actor="reasoner") == "snapshot: change 7 (reasoner)"


def test_the_author_is_recorded_without_touching_global_git_config(
    repository: SnapshotRepository,
) -> None:
    _snapshot(repository, "snapshot-000000000001.trig")
    repository.commit(commit_message(1))
    from ontoforge.gitsync.repo import _run

    author = _run(["git", "log", "-1", "--pretty=%an <%ae>"], cwd=repository.directory)
    assert author == "OntoForge <ontoforge@localhost>"


def test_a_remote_can_be_set_and_replaced(repository: SnapshotRepository) -> None:
    repository.set_remote("https://example.invalid/kg.git")
    repository.set_remote("https://example.invalid/other.git")
    from ontoforge.gitsync.repo import _run

    assert _run(["git", "remote", "-v"], cwd=repository.directory).count("origin") == 2


def test_pushing_before_initialising_is_refused(repository: SnapshotRepository) -> None:
    with pytest.raises(GitError, match="not a git repository"):
        repository.push()


def test_pushing_to_an_unreachable_remote_reports_rather_than_hangs(
    repository: SnapshotRepository,
) -> None:
    _snapshot(repository, "snapshot-000000000001.trig")
    repository.commit(commit_message(1))
    repository.set_remote("https://127.0.0.1:1/nope.git")
    with pytest.raises(GitError):
        repository.push()


def test_the_status_lists_what_would_be_committed(repository: SnapshotRepository) -> None:
    repository.initialise()
    _snapshot(repository, "snapshot-000000000001.trig")
    assert any("snapshot-" in path for path in repository.status())
