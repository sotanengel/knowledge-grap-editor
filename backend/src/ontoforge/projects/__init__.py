"""Multiple graph spaces in one installation (FR-14).

:class:`~ontoforge.projects.registry.ProjectRegistry` is deliberately *not*
re-exported here: it depends on :mod:`ontoforge.runtime`, which in turn needs
:mod:`ontoforge.projects.store`. Import it from its own module.
"""

from ontoforge.projects.store import (
    DEFAULT_PROJECT,
    Project,
    ProjectExistsError,
    ProjectNotFoundError,
    ProjectStore,
    slugify,
)

__all__ = [
    "DEFAULT_PROJECT",
    "Project",
    "ProjectExistsError",
    "ProjectNotFoundError",
    "ProjectStore",
    "slugify",
]
