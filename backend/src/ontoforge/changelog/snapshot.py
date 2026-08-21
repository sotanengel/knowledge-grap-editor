"""Snapshots and point-in-time restore (§6.4, §12.4).

A snapshot is a plain TriG dump of the whole dataset. It is portable on its own
-- drop one in a Git repository and you have a diffable backup (P3). Restoring
is "load the newest snapshot, then replay every patch recorded after it".
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from ontoforge.changelog.log import ChangeLog, apply_patch
from ontoforge.store.store import GraphStore

SNAPSHOT_SUFFIX = ".trig"
_NAME_PATTERN = re.compile(r"^snapshot-(?P<seq>\d+)-(?P<stamp>[0-9TZ]+)\.trig$")


@dataclass(frozen=True, slots=True)
class Snapshot:
    """One dataset dump on disk."""

    path: Path
    seq: int
    timestamp: datetime


@dataclass(frozen=True, slots=True)
class RestoreResult:
    """What a restore actually did."""

    from_seq: int
    replayed: int
    upto_seq: int


class SnapshotStore:
    """The ``snapshots/`` directory."""

    def __init__(self, directory: Path | str) -> None:
        self.directory = Path(directory)

    def write(self, store: GraphStore, *, seq: int) -> Snapshot:
        """Dump the whole dataset as of change ``seq``."""
        if seq < 0:
            raise ValueError("seq must not be negative")
        self.directory.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(UTC)
        stamp = timestamp.strftime("%Y%m%dT%H%M%SZ")
        path = self.directory / f"snapshot-{seq:012d}-{stamp}{SNAPSHOT_SUFFIX}"
        path.write_text(store.dump_dataset(), encoding="utf-8")
        return Snapshot(path=path, seq=seq, timestamp=timestamp)

    def all(self) -> list[Snapshot]:
        """Every snapshot, oldest first."""
        if not self.directory.is_dir():
            return []
        found: list[Snapshot] = []
        for path in self.directory.iterdir():
            match = _NAME_PATTERN.match(path.name)
            if match is None:
                continue
            found.append(
                Snapshot(
                    path=path,
                    seq=int(match["seq"]),
                    timestamp=datetime.strptime(match["stamp"], "%Y%m%dT%H%M%SZ").replace(
                        tzinfo=UTC
                    ),
                )
            )
        return sorted(found, key=lambda snapshot: (snapshot.seq, snapshot.timestamp))

    def latest(self, *, upto_seq: int | None = None) -> Snapshot | None:
        candidates = [
            snapshot for snapshot in self.all() if upto_seq is None or snapshot.seq <= upto_seq
        ]
        return candidates[-1] if candidates else None

    def prune(self, *, keep: int) -> list[Snapshot]:
        """Delete all but the ``keep`` newest snapshots; returns what was removed."""
        if keep < 0:
            raise ValueError("keep must not be negative")
        snapshots = self.all()
        doomed = snapshots[: max(len(snapshots) - keep, 0)]
        for snapshot in doomed:
            snapshot.path.unlink(missing_ok=True)
        return doomed


class SnapshotPolicy:
    """Decides when the next snapshot is due (§6.4: every N operations or on a timer)."""

    def __init__(self, *, every_ops: int | None = None, every_seconds: float | None = None) -> None:
        if every_ops is not None and every_ops < 1:
            raise ValueError("every_ops must be at least 1")
        if every_seconds is not None and every_seconds <= 0:
            raise ValueError("every_seconds must be positive")
        self.every_ops = every_ops
        self.every_seconds = every_seconds
        self._last_at: float | None = None

    @property
    def enabled(self) -> bool:
        return self.every_ops is not None or self.every_seconds is not None

    def should_snapshot(self, *, seq: int, now: float) -> bool:
        if self.every_ops is not None and seq % self.every_ops == 0:
            self._last_at = now
            return True
        if self.every_seconds is not None:
            if self._last_at is None:
                self._last_at = now
            elif now - self._last_at >= self.every_seconds:
                self._last_at = now
                return True
        return False


def restore(
    store: GraphStore,
    *,
    snapshots: SnapshotStore,
    changelog: ChangeLog,
    upto_seq: int | None = None,
) -> RestoreResult:
    """Rebuild ``store`` from the newest usable snapshot plus the patches after it."""
    store.clear()
    snapshot = snapshots.latest(upto_seq=upto_seq)
    from_seq = 0
    if snapshot is not None:
        store.load_dataset(snapshot.path.read_text(encoding="utf-8"))
        from_seq = snapshot.seq

    patches = changelog.patches_after(from_seq, upto=upto_seq)
    for patch in patches:
        apply_patch(store, patch)

    reached = patches[-1].seq if patches else from_seq
    return RestoreResult(from_seq=from_seq, replayed=len(patches), upto_seq=reached)
