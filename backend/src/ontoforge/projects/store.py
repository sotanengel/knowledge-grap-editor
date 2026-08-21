"""Several graph spaces in one installation (FR-14).

Each project owns a complete ``store / snapshots / changelog / index`` set under
``/data/projects/<id>``, so switching projects swaps the whole world rather than
filtering one. That keeps the change log, the undo stack and the search index
honest: none of them has to know that other projects exist.

An installation that predates this gets its existing ``/data`` moved into
``projects/default`` the first time it starts, so nothing is lost and nothing
has to be exported and re-imported.
"""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

DEFAULT_PROJECT = "default"
PROJECTS_DIRNAME = "projects"
METADATA_FILENAME = "project.json"
#: The directories a project owns, and the ones migration moves.
PROJECT_DIRS = ("store", "snapshots", "changelog", "index")

_SAFE_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")


class ProjectNotFoundError(LookupError):
    """Raised for a project id that does not exist."""


class ProjectExistsError(ValueError):
    """Raised when creating a project whose id is already taken."""


@dataclass(frozen=True, slots=True)
class Project:
    """One graph space."""

    id: str
    name: str
    created_at: str
    path: Path

    def as_dict(self) -> dict[str, str]:
        return {"id": self.id, "name": self.name, "createdAt": self.created_at}


def slugify(name: str) -> str:
    """A filesystem-safe id derived from a display name."""
    lowered = name.strip().lower()
    cleaned = re.sub(r"[^a-z0-9._-]+", "-", lowered).strip("-.")
    return cleaned[:64] or "project"


def check_id(project_id: str) -> str:
    """Reject anything that could escape the projects directory."""
    if not _SAFE_ID.match(project_id):
        raise ValueError(
            f"project id {project_id!r} may only contain lower-case letters, digits, . _ and -"
        )
    return project_id


class ProjectStore:
    """The ``projects/`` directory."""

    def __init__(self, data_dir: Path | str) -> None:
        self.data_dir = Path(data_dir)
        self.root = self.data_dir / PROJECTS_DIRNAME

    # ------------------------------------------------------------------ paths

    def path_for(self, project_id: str) -> Path:
        return self.root / check_id(project_id)

    def exists(self, project_id: str) -> bool:
        return (self.path_for(project_id) / METADATA_FILENAME).is_file()

    # ------------------------------------------------------------------ read

    def get(self, project_id: str) -> Project:
        path = self.path_for(project_id)
        metadata = path / METADATA_FILENAME
        if not metadata.is_file():
            raise ProjectNotFoundError(f"no project named {project_id!r}")
        record = json.loads(metadata.read_text(encoding="utf-8"))
        return Project(
            id=project_id,
            name=record.get("name", project_id),
            created_at=record.get("createdAt", ""),
            path=path,
        )

    def all(self) -> list[Project]:
        if not self.root.is_dir():
            return []
        found = [
            self.get(entry.name)
            for entry in sorted(self.root.iterdir())
            if (entry / METADATA_FILENAME).is_file()
        ]
        return sorted(found, key=lambda project: (project.id != DEFAULT_PROJECT, project.name))

    # ------------------------------------------------------------------ write

    def create(self, *, name: str, project_id: str | None = None) -> Project:
        """Create a project. Without an id -- or with a blank one -- it is
        derived from the name."""
        cleaned = name.strip()
        if not cleaned:
            raise ValueError("a project needs a name")

        resolved = check_id(
            project_id.strip() if project_id and project_id.strip() else slugify(cleaned)
        )
        if self.exists(resolved):
            raise ProjectExistsError(f"a project named {resolved!r} already exists")

        path = self.path_for(resolved)
        for directory in PROJECT_DIRS:
            (path / directory).mkdir(parents=True, exist_ok=True)
        record = {"name": cleaned, "createdAt": datetime.now(UTC).isoformat()}
        (path / METADATA_FILENAME).write_text(json.dumps(record, indent=2), encoding="utf-8")
        return self.get(resolved)

    def rename(self, project_id: str, name: str) -> Project:
        project = self.get(project_id)
        cleaned = name.strip()
        if not cleaned:
            raise ValueError("a project needs a name")
        record = {"name": cleaned, "createdAt": project.created_at}
        (project.path / METADATA_FILENAME).write_text(
            json.dumps(record, indent=2), encoding="utf-8"
        )
        return self.get(project_id)

    def delete(self, project_id: str) -> None:
        """Remove a project and everything in it. The default one stays."""
        if project_id == DEFAULT_PROJECT:
            raise ValueError("the default project cannot be deleted")
        project = self.get(project_id)
        shutil.rmtree(project.path)

    # ------------------------------------------------------------------ migration

    def ensure_default(self) -> Project:
        """Guarantee a default project, adopting any pre-existing single graph."""
        if self.exists(DEFAULT_PROJECT):
            return self.get(DEFAULT_PROJECT)

        created = self.create(name="デフォルト", project_id=DEFAULT_PROJECT)
        self._adopt_legacy_layout(created)
        return created

    def _adopt_legacy_layout(self, project: Project) -> None:
        """Move a pre-projects ``/data/{store,...}`` into the default project."""
        for directory in PROJECT_DIRS:
            source = self.data_dir / directory
            target = project.path / directory
            if not source.is_dir():
                continue
            if not any(source.iterdir()):
                # An empty leftover has nothing to move and only invites
                # confusion about which layout is live, so it goes.
                source.rmdir()
                continue
            if target.is_dir() and any(target.iterdir()):
                continue
            shutil.rmtree(target, ignore_errors=True)
            shutil.move(str(source), str(target))
