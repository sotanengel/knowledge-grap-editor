"""Keeping snapshots in Git (§12.4, §14 Phase 3).

§12.4 recommends putting ``snapshots/*.trig`` in a repository and diffing them.
This automates the recommendation: after each snapshot, commit it.

Only the snapshots directory is versioned. The RocksDB store is binary and
rewritten wholesale, so committing it would produce enormous useless diffs; a
TriG dump is text, and a text diff of a knowledge graph is worth reading.

Pushing is opt-in and credentials come from the environment, never from a file
this project writes.
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

DEFAULT_BRANCH = "main"
DEFAULT_AUTHOR_NAME = "OntoForge"
DEFAULT_AUTHOR_EMAIL = "ontoforge@localhost"
COMMAND_TIMEOUT_SECONDS = 60


class GitError(RuntimeError):
    """Raised when a git command fails."""


@dataclass(frozen=True, slots=True)
class CommitResult:
    """What a commit attempt did."""

    committed: bool
    revision: str | None = None
    message: str = ""
    files: int = 0


def git_available() -> bool:
    """Whether git is on the path at all."""
    try:
        _run(["git", "--version"], cwd=Path.cwd())
    except GitError:
        return False
    return True


def _run(arguments: Sequence[str], *, cwd: Path, env: Mapping[str, str] | None = None) -> str:
    try:
        completed = subprocess.run(
            list(arguments),
            cwd=cwd,
            env={**os.environ, **(env or {})},
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT_SECONDS,
            check=False,
        )
    except FileNotFoundError as error:
        raise GitError("git is not installed") from error
    except subprocess.TimeoutExpired as error:
        raise GitError(f"git {arguments[1] if len(arguments) > 1 else ''} timed out") from error

    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        raise GitError(f"git {' '.join(arguments[1:])} failed: {detail}")
    return completed.stdout.strip()


class SnapshotRepository:
    """A git repository over the snapshots directory."""

    def __init__(
        self,
        directory: Path | str,
        *,
        branch: str = DEFAULT_BRANCH,
        author_name: str = DEFAULT_AUTHOR_NAME,
        author_email: str = DEFAULT_AUTHOR_EMAIL,
    ) -> None:
        self.directory = Path(directory)
        self.branch = branch
        self.author_name = author_name
        self.author_email = author_email

    @property
    def initialised(self) -> bool:
        return (self.directory / ".git").is_dir()

    def _env(self) -> dict[str, str]:
        return {
            "GIT_AUTHOR_NAME": self.author_name,
            "GIT_AUTHOR_EMAIL": self.author_email,
            "GIT_COMMITTER_NAME": self.author_name,
            "GIT_COMMITTER_EMAIL": self.author_email,
            # Nothing here should ever wait for a password prompt.
            "GIT_TERMINAL_PROMPT": "0",
        }

    def initialise(self) -> None:
        """Create the repository if it is not there yet."""
        self.directory.mkdir(parents=True, exist_ok=True)
        if self.initialised:
            return
        _run(["git", "init", "--initial-branch", self.branch], cwd=self.directory)
        gitignore = self.directory / ".gitignore"
        if not gitignore.exists():
            gitignore.write_text("# Only the TriG snapshots are versioned.\n*.tmp\n", "utf-8")

    def status(self) -> list[str]:
        """Paths that differ from the last commit."""
        if not self.initialised:
            return []
        output = _run(["git", "status", "--porcelain"], cwd=self.directory, env=self._env())
        return [line[3:] for line in output.splitlines() if line.strip()]

    def commit(self, message: str) -> CommitResult:
        """Commit whatever changed. Nothing changed means no commit."""
        self.initialise()
        pending = self.status()
        if not pending:
            return CommitResult(committed=False, message="nothing to commit")

        _run(["git", "add", "-A"], cwd=self.directory, env=self._env())
        _run(["git", "commit", "-m", message], cwd=self.directory, env=self._env())
        revision = _run(["git", "rev-parse", "HEAD"], cwd=self.directory, env=self._env())
        return CommitResult(committed=True, revision=revision, message=message, files=len(pending))

    def log(self, limit: int = 20) -> list[dict[str, str]]:
        if not self.initialised:
            return []
        output = _run(
            ["git", "log", f"-{limit}", "--pretty=format:%H%x1f%aI%x1f%s"],
            cwd=self.directory,
            env=self._env(),
        )
        entries: list[dict[str, str]] = []
        for line in output.splitlines():
            revision, timestamp, subject = line.split("\x1f", 2)
            entries.append({"revision": revision, "timestamp": timestamp, "subject": subject})
        return entries

    def set_remote(self, url: str, *, name: str = "origin") -> None:
        self.initialise()
        existing = _run(["git", "remote"], cwd=self.directory, env=self._env()).split()
        verb = "set-url" if name in existing else "add"
        _run(["git", "remote", verb, name, url], cwd=self.directory, env=self._env())

    def push(self, *, remote: str = "origin") -> str:
        """Push the branch. Credentials come from the environment (§13)."""
        if not self.initialised:
            raise GitError("the snapshots directory is not a git repository yet")
        return _run(
            ["git", "push", "--set-upstream", remote, self.branch],
            cwd=self.directory,
            env=self._env(),
        )


def commit_message(seq: int, *, actor: str = "user") -> str:
    """A subject line that says what the snapshot is, for a readable log."""
    return f"snapshot: change {seq} ({actor})"
