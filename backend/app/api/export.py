from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from app.deps import get_export_service
from app.services.export_service import ExportService

router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("")
def export_rdf(
    format: str = Query("turtle", alias="format"),
    export: ExportService = Depends(get_export_service),
) -> Response:
    try:
        content, media_type, ext = export.export(format)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="knowledge-graph.{ext}"'},
    )
