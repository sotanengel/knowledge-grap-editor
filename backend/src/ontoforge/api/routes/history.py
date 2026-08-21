"""Change history, undo and redo (§8, FR-12)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from ontoforge.api.deps import RuntimeDep
from ontoforge.api.schemas import HistoryEntry, HistoryPage
from ontoforge.changelog.patch import Patch

router = APIRouter(prefix="/history", tags=["history"])


def _entry(patch: Patch) -> HistoryEntry:
    return HistoryEntry(
        seq=patch.seq,
        id=patch.id,
        actor=patch.actor,
        timestamp=patch.timestamp.isoformat(),
        additions=len(patch.additions),
        deletions=len(patch.deletions),
        inverse_of=patch.inverse_of,
    )


@router.get("", response_model=HistoryPage)
def get_history(
    runtime: RuntimeDep,
    limit: int = Query(default=50, ge=1, le=1000),
) -> HistoryPage:
    """Recorded changes, newest first."""
    return HistoryPage(
        entries=[_entry(patch) for patch in runtime.changelog.history(limit=limit)],
        can_undo=runtime.changelog.can_undo,
        can_redo=runtime.changelog.can_redo,
    )


@router.post("/undo", response_model=HistoryEntry)
def undo(runtime: RuntimeDep) -> HistoryEntry:
    """Undo the last change by appending its inverse -- the log is never rewritten."""
    patch = runtime.undo()
    if patch is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "there is nothing to undo")
    return _entry(patch)


@router.post("/redo", response_model=HistoryEntry)
def redo(runtime: RuntimeDep) -> HistoryEntry:
    patch = runtime.redo()
    if patch is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "there is nothing to redo")
    return _entry(patch)
