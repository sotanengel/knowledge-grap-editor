from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.helpers import raise_if_blocked
from app.deps import get_graph_service, get_validation_service
from app.models.schemas import Node, NodeCreate, NodeUpdate
from app.services.graph_service import GraphService
from app.services.validation_service import ValidationService

router = APIRouter(prefix="/api/nodes", tags=["nodes"])


@router.get("", response_model=list[Node])
def list_nodes(
    type: str | None = Query(None, alias="type"),
    graph: GraphService = Depends(get_graph_service),
) -> list[Node]:
    return graph.list_nodes(type_filter=type)


@router.get("/{node_id}", response_model=Node)
def get_node(node_id: str, graph: GraphService = Depends(get_graph_service)) -> Node:
    node = graph.get_node(node_id)
    if not node:
        raise HTTPException(status_code=404, detail="ノードが見つかりません")
    return node


@router.post("", response_model=Node, status_code=201)
def create_node(
    data: NodeCreate,
    graph: GraphService = Depends(get_graph_service),
    validation: ValidationService = Depends(get_validation_service),
) -> Node:
    if graph.get_node(data.id):
        raise HTTPException(status_code=409, detail="同じ ID のノードが既に存在します")
    warnings = validation.validate_node(data)
    raise_if_blocked(warnings, validation.should_block(warnings))
    node = graph.create_node(data)
    if warnings:
        node_dict = node.model_dump()
        node_dict["warnings"] = [w.model_dump() for w in warnings]
        return node_dict  # type: ignore[return-value]
    return node


@router.put("/{node_id}", response_model=Node)
def update_node(
    node_id: str,
    data: NodeUpdate,
    graph: GraphService = Depends(get_graph_service),
    validation: ValidationService = Depends(get_validation_service),
) -> Node:
    existing = graph.get_node(node_id)
    if not existing:
        raise HTTPException(status_code=404, detail="ノードが見つかりません")
    merged = NodeCreate(
        id=node_id,
        label=data.label or existing.label,
        type=data.type or existing.type,
        properties=data.properties if data.properties is not None else existing.properties,
    )
    warnings = validation.validate_node(merged)
    raise_if_blocked(warnings, validation.should_block(warnings))
    node = graph.update_node(node_id, data)
    if not node:
        raise HTTPException(status_code=404, detail="ノードが見つかりません")
    return node


@router.delete("/{node_id}", status_code=204)
def delete_node(node_id: str, graph: GraphService = Depends(get_graph_service)) -> None:
    if not graph.delete_node(node_id):
        raise HTTPException(status_code=404, detail="ノードが見つかりません")


@router.get("/{node_id}/neighbors")
def get_neighbors(
    node_id: str,
    depth: int = Query(1, ge=1, le=5),
    graph: GraphService = Depends(get_graph_service),
):
    result = graph.get_neighbors(node_id, depth=depth)
    if not result:
        raise HTTPException(status_code=404, detail="ノードが見つかりません")
    return result
