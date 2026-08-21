"""Versioning snapshots with Git (§12.4, §14 Phase 3)."""

from ontoforge.gitsync.repo import (
    CommitResult,
    GitError,
    SnapshotRepository,
    commit_message,
    git_available,
)

__all__ = [
    "CommitResult",
    "GitError",
    "SnapshotRepository",
    "commit_message",
    "git_available",
]
