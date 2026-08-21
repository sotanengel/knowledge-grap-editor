"""Import, export and saved CSV mappings (§8, §11)."""

from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Query, Response, UploadFile, status
from pydantic import ValidationError
from pyoxigraph import NamedNode

from ontoforge.api.deps import MappingDep, TransferDep
from ontoforge.api.schemas import ImportSummary, MappingNames
from ontoforge.io.csvmap import CsvMapping
from ontoforge.io.formats import ExportFormat, ImportFormat, file_extension, media_type
from ontoforge.io.service import UnsupportedFormatError
from ontoforge.store import graphs

router = APIRouter(tags=["transfer"])

EXPORT_FILENAME = "ontoforge"


@router.post("/import", response_model=ImportSummary)
async def import_file(
    transfer: TransferDep,
    mappings: MappingDep,
    file: Annotated[UploadFile, File()],
    mapping: Annotated[str | None, Form()] = None,
    mapping_name: Annotated[str | None, Form()] = None,
) -> ImportSummary:
    """Load an uploaded file. CSV needs a column mapping; RDF does not."""
    filename = file.filename or "upload"
    payload = await file.read()

    definition = _resolve_mapping(mapping, mapping_name, mappings)
    try:
        if definition is not None:
            result = transfer.import_csv(payload, mapping=definition, filename=filename)
        else:
            result = transfer.import_rdf(payload, filename=filename)
    except UnsupportedFormatError as error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(error)) from error
    except ValueError as error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(error)) from error

    return ImportSummary(
        quads=result.quads, rows=result.rows, iris=result.iris, format=result.format
    )


def _resolve_mapping(
    inline: str | None, name: str | None, mappings: MappingDep
) -> CsvMapping | None:
    if inline:
        try:
            return CsvMapping.model_validate(json.loads(inline))
        except (json.JSONDecodeError, ValidationError) as error:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, f"the mapping is not usable: {error}"
            ) from error
    if name:
        try:
            return mappings.load(name)
        except LookupError as error:
            raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error
    return None


@router.get("/export")
def export_graph(
    transfer: TransferDep,
    format: str = ExportFormat.TURTLE.value,
    selection: Annotated[str | None, Query(alias="graphs")] = None,
) -> Response:
    """Serialise the selected named graphs in the requested format."""
    selected = _selected_graphs(selection)
    try:
        payload = transfer.export(format, named_graphs=selected)
    except UnsupportedFormatError as error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(error)) from error

    filename = f"{EXPORT_FILENAME}.{file_extension(format)}"
    return Response(
        content=payload,
        media_type=media_type(format),
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _selected_graphs(raw: str | None) -> tuple[NamedNode, ...]:
    if not raw:
        return graphs.DEFAULT_EXPORT
    names = [part.strip() for part in raw.split(",") if part.strip()]
    if not names:
        return graphs.DEFAULT_EXPORT
    return tuple(NamedNode(name) for name in names)


@router.get("/mappings", response_model=MappingNames)
def list_mappings(mappings: MappingDep) -> MappingNames:
    return MappingNames(names=mappings.names())


@router.get("/mappings/{name}", response_model=CsvMapping)
def get_mapping(name: str, mappings: MappingDep) -> CsvMapping:
    try:
        return mappings.load(name)
    except LookupError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error
    except ValueError as error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(error)) from error


@router.put("/mappings/{name}", response_model=CsvMapping)
def put_mapping(name: str, body: CsvMapping, mappings: MappingDep) -> CsvMapping:
    """Save a mapping so the next import of the same shape is one click (FR-13)."""
    if body.name != name:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"body names {body.name!r} but the path says {name!r}"
        )
    mappings.save(body)
    return body


@router.delete("/mappings/{name}")
def delete_mapping(name: str, mappings: MappingDep) -> dict[str, bool]:
    try:
        return {"deleted": mappings.delete(name)}
    except ValueError as error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(error)) from error


__all__ = ["ImportFormat", "router"]
