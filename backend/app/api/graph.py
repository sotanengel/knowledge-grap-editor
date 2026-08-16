from fastapi import APIRouter, Depends, Query

from app.deps import get_graph_service
from app.models.schemas import GraphSearchResult
from app.services.graph_service import GraphService

router = APIRouter(prefix="/api/graph", tags=["graph"])


@router.get("/search", response_model=GraphSearchResult)
def search_graph(
    q: str = Query(..., min_length=1),
    graph: GraphService = Depends(get_graph_service),
) -> GraphSearchResult:
    return graph.search(q)


@router.get("/relationship")
def find_relationship(
    source: str = Query(...),
    target: str = Query(...),
    graph: GraphService = Depends(get_graph_service),
):
    paths = graph.find_relationship_path(source, target)
    return {"paths": paths}
