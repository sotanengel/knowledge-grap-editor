"""Holding one open runtime per project (FR-14).

Switching projects swaps the whole runtime -- store, change log, undo stack and
indexes together -- because those are exactly the things that must not leak
between graph spaces. Runtimes are opened lazily and kept, so switching back and
forth does not re-open RocksDB every time; :meth:`close` releases them all.
"""

from __future__ import annotations

from types import TracebackType
from typing import Self

from ontoforge.config import Settings
from ontoforge.projects.store import DEFAULT_PROJECT, ProjectNotFoundError, ProjectStore
from ontoforge.runtime import Runtime


class ProjectRegistry:
    """The open runtimes, keyed by project id."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.projects = ProjectStore(settings.data_dir)
        self.projects.ensure_default()
        self._runtimes: dict[str, Runtime] = {}
        self._current = (
            settings.project if self.projects.exists(settings.project) else DEFAULT_PROJECT
        )

    # ------------------------------------------------------------------ current

    @property
    def current_id(self) -> str:
        return self._current

    @property
    def current(self) -> Runtime:
        return self.open(self._current)

    def switch(self, project_id: str) -> Runtime:
        """Make ``project_id`` the one requests act on."""
        if not self.projects.exists(project_id):
            raise ProjectNotFoundError(f"no project named {project_id!r}")
        self._current = project_id
        return self.current

    # ------------------------------------------------------------------ runtimes

    def open(self, project_id: str) -> Runtime:
        existing = self._runtimes.get(project_id)
        if existing is not None:
            return existing
        if not self.projects.exists(project_id):
            raise ProjectNotFoundError(f"no project named {project_id!r}")
        runtime = Runtime.create(self.settings.for_project(project_id))
        self._runtimes[project_id] = runtime
        return runtime

    def release(self, project_id: str) -> None:
        """Close one runtime, e.g. before deleting the project it belongs to."""
        runtime = self._runtimes.pop(project_id, None)
        if runtime is not None:
            runtime.close()

    def delete(self, project_id: str) -> None:
        self.release(project_id)
        self.projects.delete(project_id)
        if self._current == project_id:
            self._current = DEFAULT_PROJECT

    def close(self) -> None:
        for runtime in self._runtimes.values():
            runtime.close()
        self._runtimes.clear()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()
