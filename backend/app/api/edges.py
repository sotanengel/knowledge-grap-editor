from fastapi import APIRouter, Depends, HTTPException

from app.api.helpers import raise_if_blocked
from app.deps import get_graph_service, get_validation_service
from app.models.schemas import Edge, EdgeCreate, EdgeUpdate
from app.services.graph_service import GraphService
from app.services.validation_service import ValidationService

router = APIRouter(prefix="/api/edges", tags=["edges"])


@router.get("", response_model=list[Edge])
def list_edges(graph: GraphService = Depends(get_graph_service)) -> list[Edge]:
    return graph.list_edges()


@router.get("/{edge_id}", response_model=Edge)
def get_edge(edge_id: str, graph: GraphService = Depends(get_graph_service)) -> Edge:
    edge = graph.get_edge(edge_id)
    if not edge:
        raise HTTPException(status_code=404, detail="エッジが見つかりません")
    return edge


@router.post("", response_model=Edge, status_code=201)
def create_edge(
    data: EdgeCreate,
    graph: GraphService = Depends(get_graph_service),
    validation: ValidationService = Depends(get_validation_service),
) -> Edge:
    if graph.get_edge(data.id):
        raise HTTPException(status_code=409, detail="同じ ID のエッジが既に存在します")
    warnings = validation.validate_edge(data)
    raise_if_blocked(warnings, validation.should_block(warnings))
    return graph.create_edge(data)


@router.put("/{edge_id}", response_model=Edge)
def update_edge(
    edge_id: str,
    data: EdgeUpdate,
    graph: GraphService = Depends(get_graph_service),
    validation: ValidationService = Depends(get_validation_service),
) -> Edge:
    existing = graph.get_edge(edge_id)
    if not existing:
        raise HTTPException(status_code=404, detail="エッジが見つかりません")
    merged = EdgeCreate(
        id=edge_id,
        subject=data.subject or existing.subject,
        predicate=data.predicate or existing.predicate,
        object=data.object or existing.object,
        properties=data.properties if data.properties is not None else existing.properties,
    )
    warnings = validation.validate_edge(merged)
    raise_if_blocked(warnings, validation.should_block(warnings))
    edge = graph.update_edge(edge_id, data)
    if not edge:
        raise HTTPException(status_code=404, detail="エッジが見つかりません")
    return edge


@router.delete("/{edge_id}", status_code=204)
def delete_edge(edge_id: str, graph: GraphService = Depends(get_graph_service)) -> None:
    if not graph.delete_edge(edge_id):
        raise HTTPException(status_code=404, detail="エッジが見つかりません")
