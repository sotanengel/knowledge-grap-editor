"""Project management and the Phase 3 extras (FR-14, §12.4, §14 Phase 3)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request, status

from ontoforge.api.deps import RuntimeDep, registry_of
from ontoforge.api.schemas import CreateProject, RenameProject, SetGitRemote
from ontoforge.gitsync.repo import (
    GitError,
    SnapshotRepository,
    commit_message,
    git_available,
)
from ontoforge.projects.store import ProjectExistsError, ProjectNotFoundError
from ontoforge.runtime import Runtime

router = APIRouter(tags=["projects"])


# ---------------------------------------------------------------------- projects


@router.get("/projects")
def list_projects(request: Request) -> dict[str, Any]:
    registry = registry_of(request)
    return {
        "current": registry.current_id,
        "projects": [project.as_dict() for project in registry.projects.all()],
    }


@router.post("/projects", status_code=status.HTTP_201_CREATED)
def create_project(body: CreateProject, request: Request) -> dict[str, Any]:
    registry = registry_of(request)
    try:
        project = registry.projects.create(name=body.name, project_id=body.id)
    except ProjectExistsError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error
    except ValueError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(error)) from error
    return project.as_dict()


@router.post("/projects/{project_id}/switch")
def switch_project(project_id: str, request: Request) -> dict[str, Any]:
    """Swap the whole graph space: store, history, undo stack and indexes."""
    registry = registry_of(request)
    try:
        registry.switch(project_id)
    except (ProjectNotFoundError, ValueError) as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error
    return {"current": registry.current_id}


@router.patch("/projects/{project_id}")
def rename_project(project_id: str, body: RenameProject, request: Request) -> dict[str, Any]:
    registry = registry_of(request)
    try:
        return registry.projects.rename(project_id, body.name).as_dict()
    except ProjectNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error
    except ValueError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(error)) from error


@router.delete("/projects/{project_id}")
def delete_project(project_id: str, request: Request) -> dict[str, Any]:
    registry = registry_of(request)
    try:
        registry.delete(project_id)
    except ProjectNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error
    except ValueError as error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(error)) from error
    return {"deleted": project_id, "current": registry.current_id}


# ---------------------------------------------------------------------- semantic


@router.get("/semantic")
def semantic_status(runtime: RuntimeDep) -> dict[str, Any]:
    """Whether vector search is on, and what it can and cannot do."""
    return {
        "enabled": runtime.vectors is not None,
        "indexed": runtime.vectors.count() if runtime.vectors else 0,
        "note": (
            "ラベルの文字 n-gram による類似検索です。学習済み埋め込みではないため、"
            "表記のゆれや部分一致には強い一方、意味の近さは捉えません。"
            "ONTOFORGE_SEMANTIC_SEARCH=1 で有効になります。"
        ),
    }


@router.get("/semantic/search")
def semantic_search(
    runtime: RuntimeDep,
    q: str,
    limit: int = Query(default=10, ge=1, le=100),
) -> dict[str, Any]:
    if runtime.vectors is None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "semantic search is off; set ONTOFORGE_SEMANTIC_SEARCH=1 to enable it",
        )
    hits = runtime.vectors.search(q, limit=limit)
    return {
        "results": [
            {"iri": hit.iri, "label": hit.label, "score": round(hit.score, 4)} for hit in hits
        ]
    }


@router.post("/semantic/reindex")
def semantic_reindex(runtime: RuntimeDep) -> dict[str, int]:
    if runtime.vectors is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "semantic search is off")
    runtime.reindex_all()
    return {"indexed": runtime.vectors.count()}


# ---------------------------------------------------------------------- git


@router.get("/git")
def git_status(runtime: RuntimeDep) -> dict[str, Any]:
    """Whether snapshots are versioned, and what the log looks like (§12.4)."""
    repository = runtime.git
    return {
        "available": git_available(),
        "enabled": repository is not None,
        "initialised": repository.initialised if repository else False,
        "pending": repository.status() if repository else [],
        "log": repository.log(limit=20) if repository else [],
        "remote": runtime.settings.git_remote,
    }


@router.post("/git/commit")
def git_commit(runtime: RuntimeDep) -> dict[str, Any]:
    repository = _repository(runtime)
    try:
        result = repository.commit(commit_message(runtime.changelog.last_seq))
    except GitError as error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(error)) from error
    return {"committed": result.committed, "revision": result.revision, "files": result.files}


@router.put("/git/remote")
def git_set_remote(body: SetGitRemote, runtime: RuntimeDep) -> dict[str, str]:
    repository = _repository(runtime)
    try:
        repository.set_remote(body.url)
    except GitError as error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(error)) from error
    return {"remote": body.url}


@router.post("/git/push")
def git_push(runtime: RuntimeDep) -> dict[str, str]:
    """Push the snapshot repository. Credentials come from the environment (§13)."""
    repository = _repository(runtime)
    try:
        return {"output": repository.push()}
    except GitError as error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(error)) from error


def _repository(runtime: Runtime) -> SnapshotRepository:
    if runtime.git is None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "snapshot versioning is off; set ONTOFORGE_GIT_SNAPSHOTS=1 to enable it",
        )
    return runtime.git
