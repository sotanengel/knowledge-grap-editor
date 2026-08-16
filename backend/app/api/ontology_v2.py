"""v2 ontology API endpoints."""

from fastapi import APIRouter, Depends, HTTPException

from app.deps import get_ontology_service, get_suggest_service
from app.models.schemas import (
    ConsistencyReportSchema,
    OwlClassCreateV2,
    OwlClassUpdateV2,
    OwlClassV2,
    OwlPropertyCreateV2,
    OwlPropertyUpdateV2,
    OwlPropertyV2,
    SchemaV2Response,
    SimilarClassWarning,
    SuggestResponse,
    TripleSchema,
)
from app.services.ontology_service import OntologyService
from app.services.suggest_service import SuggestService

router = APIRouter(prefix="/api/ontology/v2", tags=["ontology-v2"])


@router.get("/schema", response_model=SchemaV2Response)
def get_schema_v2(ontology: OntologyService = Depends(get_ontology_service)) -> SchemaV2Response:
    return ontology.tbox.get_schema_v2()


@router.get("/classes", response_model=list[OwlClassV2])
def list_classes_v2(
    ontology: OntologyService = Depends(get_ontology_service),
) -> list[OwlClassV2]:
    return ontology.tbox.list_classes_v2()


@router.get("/classes/{class_id}", response_model=OwlClassV2)
def get_class_v2(
    class_id: str, ontology: OntologyService = Depends(get_ontology_service)
) -> OwlClassV2:
    cls = ontology.tbox.get_class_v2(class_id)
    if not cls:
        raise HTTPException(status_code=404, detail="Class が見つかりません")
    return cls


@router.post("/classes", response_model=OwlClassV2, status_code=201)
def create_class_v2(
    data: OwlClassCreateV2,
    ontology: OntologyService = Depends(get_ontology_service),
    suggest: SuggestService = Depends(get_suggest_service),
) -> OwlClassV2:
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
    return ontology.tbox.create_class_v2(data)


@router.put("/classes/{class_id}", response_model=OwlClassV2)
def update_class_v2(
    class_id: str,
    data: OwlClassUpdateV2,
    ontology: OntologyService = Depends(get_ontology_service),
) -> OwlClassV2:
    cls = ontology.tbox.update_class_v2(class_id, data)
    if not cls:
        raise HTTPException(status_code=404, detail="Class が見つかりません")
    return cls


@router.delete("/classes/{class_id}", status_code=204)
def delete_class_v2(
    class_id: str, ontology: OntologyService = Depends(get_ontology_service)
) -> None:
    if not ontology.delete_class(class_id):
        raise HTTPException(status_code=404, detail="Class が見つかりません")


@router.get("/properties", response_model=list[OwlPropertyV2])
def list_properties_v2(
    ontology: OntologyService = Depends(get_ontology_service),
) -> list[OwlPropertyV2]:
    return ontology.tbox.list_properties_v2()


@router.get("/properties/{prop_id}", response_model=OwlPropertyV2)
def get_property_v2(
    prop_id: str, ontology: OntologyService = Depends(get_ontology_service)
) -> OwlPropertyV2:
    prop = ontology.tbox.get_property_v2(prop_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property が見つかりません")
    return prop


@router.post("/properties", response_model=OwlPropertyV2, status_code=201)
def create_property_v2(
    data: OwlPropertyCreateV2,
    ontology: OntologyService = Depends(get_ontology_service),
) -> OwlPropertyV2:
    if ontology.tbox.get_property_v2(data.id):
        raise HTTPException(status_code=409, detail="同じ ID の Property が既に存在します")
    return ontology.tbox.create_property_v2(data)


@router.put("/properties/{prop_id}", response_model=OwlPropertyV2)
def update_property_v2(
    prop_id: str,
    data: OwlPropertyUpdateV2,
    ontology: OntologyService = Depends(get_ontology_service),
) -> OwlPropertyV2:
    prop = ontology.tbox.update_property_v2(prop_id, data)
    if not prop:
        raise HTTPException(status_code=404, detail="Property が見つかりません")
    return prop


@router.delete("/properties/{prop_id}", status_code=204)
def delete_property_v2(
    prop_id: str, ontology: OntologyService = Depends(get_ontology_service)
) -> None:
    if not ontology.tbox.delete_property_v2(prop_id):
        raise HTTPException(status_code=404, detail="Property が見つかりません")


@router.get("/consistency", response_model=ConsistencyReportSchema)
def get_consistency(
    ontology: OntologyService = Depends(get_ontology_service),
) -> ConsistencyReportSchema:
    return ontology.tbox.get_consistency_report()


@router.get("/inferred", response_model=list[TripleSchema])
def list_inferred_triples(
    ontology: OntologyService = Depends(get_ontology_service),
) -> list[TripleSchema]:
    return ontology.tbox.list_inferred_triples()


@router.get("/suggest", response_model=SuggestResponse)
def suggest_classes_v2(
    q: str = "",
    suggest: SuggestService = Depends(get_suggest_service),
) -> SuggestResponse:
    return suggest.suggest_classes(q)
