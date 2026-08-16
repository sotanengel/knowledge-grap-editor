from fastapi import APIRouter, Depends, HTTPException

from app.deps import get_ontology_service, get_suggest_service
from app.models.schemas import (
    ClassCreate,
    ClassUpdate,
    OntologyClass,
    PropertyCreate,
    PropertyDef,
    Relationship,
    RelationshipCreate,
    RelationshipUpdate,
    SchemaResponse,
    SimilarClassWarning,
    SuggestResponse,
)
from app.services.ontology_service import OntologyService
from app.services.suggest_service import SuggestService

router = APIRouter(prefix="/api/ontology", tags=["ontology"])


@router.get("/classes", response_model=list[OntologyClass])
def list_classes(ontology: OntologyService = Depends(get_ontology_service)) -> list[OntologyClass]:
    return ontology.list_classes()


@router.get("/classes/{class_id}", response_model=OntologyClass)
def get_class(
    class_id: str, ontology: OntologyService = Depends(get_ontology_service)
) -> OntologyClass:
    cls = ontology.get_class(class_id)
    if not cls:
        raise HTTPException(status_code=404, detail="Class が見つかりません")
    return cls


@router.get("/classes/{class_id}/properties", response_model=list[PropertyDef])
def get_class_properties(
    class_id: str, ontology: OntologyService = Depends(get_ontology_service)
) -> list[PropertyDef]:
    if not ontology.get_class(class_id):
        raise HTTPException(status_code=404, detail="Class が見つかりません")
    return ontology.get_class_properties(class_id)


@router.post("/classes", response_model=OntologyClass, status_code=201)
def create_class(
    data: ClassCreate,
    ontology: OntologyService = Depends(get_ontology_service),
    suggest: SuggestService = Depends(get_suggest_service),
) -> OntologyClass:
    if ontology.get_class(data.id):
        raise HTTPException(status_code=409, detail="同じ ID の Class が既に存在します")
    if not data.force:
        similar = suggest.find_similar_classes(data.label or data.id)
        if similar.results and similar.results[0].id != data.id:
            raise HTTPException(
                status_code=409,
                detail=SimilarClassWarning(
                    message="類似する既存型があります。既存型を利用しますか？",
                    similar=similar.results,
                ).model_dump(),
            )
    return ontology.create_class(data)


@router.put("/classes/{class_id}", response_model=OntologyClass)
def update_class(
    class_id: str,
    data: ClassUpdate,
    ontology: OntologyService = Depends(get_ontology_service),
) -> OntologyClass:
    cls = ontology.update_class(class_id, data)
    if not cls:
        raise HTTPException(status_code=404, detail="Class が見つかりません")
    return cls


@router.delete("/classes/{class_id}", status_code=204)
def delete_class(class_id: str, ontology: OntologyService = Depends(get_ontology_service)) -> None:
    if not ontology.delete_class(class_id):
        raise HTTPException(status_code=404, detail="Class が見つかりません")


@router.get("/properties", response_model=list[PropertyDef])
def list_properties(
    ontology: OntologyService = Depends(get_ontology_service),
) -> list[PropertyDef]:
    return ontology.list_properties()


@router.post("/properties", response_model=PropertyDef, status_code=201)
def create_property(
    data: PropertyCreate,
    ontology: OntologyService = Depends(get_ontology_service),
) -> PropertyDef:
    return ontology.create_property(data)


@router.get("/relationships", response_model=list[Relationship])
def list_relationships(
    ontology: OntologyService = Depends(get_ontology_service),
) -> list[Relationship]:
    return ontology.list_relationships()


@router.get("/relationships/{rel_id}", response_model=Relationship)
def get_relationship(
    rel_id: str, ontology: OntologyService = Depends(get_ontology_service)
) -> Relationship:
    rel = ontology.get_relationship(rel_id)
    if not rel:
        raise HTTPException(status_code=404, detail="Relationship が見つかりません")
    return rel


@router.post("/relationships", response_model=Relationship, status_code=201)
def create_relationship(
    data: RelationshipCreate,
    ontology: OntologyService = Depends(get_ontology_service),
) -> Relationship:
    if ontology.get_relationship(data.id):
        raise HTTPException(status_code=409, detail="同じ ID の Relationship が既に存在します")
    return ontology.create_relationship(data)


@router.put("/relationships/{rel_id}", response_model=Relationship)
def update_relationship(
    rel_id: str,
    data: RelationshipUpdate,
    ontology: OntologyService = Depends(get_ontology_service),
) -> Relationship:
    rel = ontology.update_relationship(rel_id, data)
    if not rel:
        raise HTTPException(status_code=404, detail="Relationship が見つかりません")
    return rel


@router.delete("/relationships/{rel_id}", status_code=204)
def delete_relationship(
    rel_id: str, ontology: OntologyService = Depends(get_ontology_service)
) -> None:
    if not ontology.delete_relationship(rel_id):
        raise HTTPException(status_code=404, detail="Relationship が見つかりません")


@router.get("/suggest", response_model=SuggestResponse)
def suggest_classes(
    q: str = "",
    suggest: SuggestService = Depends(get_suggest_service),
) -> SuggestResponse:
    return suggest.suggest_classes(q)


@router.get("/suggest/relationships", response_model=SuggestResponse)
def suggest_relationships(
    q: str,
    suggest: SuggestService = Depends(get_suggest_service),
) -> SuggestResponse:
    return suggest.suggest_relationships(q)


@router.get("/schema", response_model=SchemaResponse)
def get_schema(ontology: OntologyService = Depends(get_ontology_service)) -> SchemaResponse:
    return ontology.get_schema()
