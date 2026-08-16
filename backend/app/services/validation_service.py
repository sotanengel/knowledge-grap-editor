from __future__ import annotations

from app.config import settings
from app.models.schemas import (
    EdgeCreate,
    NodeCreate,
    ValidationWarning,
)
from app.services.graph_service import GraphService
from app.services.ontology_service import OntologyService


class ValidationService:
    def __init__(
        self,
        ontology: OntologyService,
        graph: GraphService,
    ) -> None:
        self.ontology = ontology
        self.graph = graph

    def validate_node(self, data: NodeCreate) -> list[ValidationWarning]:
        warnings: list[ValidationWarning] = []
        cls = self.ontology.get_class(data.type)
        if not cls:
            warnings.append(
                ValidationWarning(
                    code="INVALID_NODE_TYPE",
                    message=f"型 '{data.type}' はオントロジーに定義されていません。",
                    field="type",
                )
            )
            return warnings

        for prop in self.ontology.list_properties():
            if prop.required and prop.id not in data.properties:
                if not prop.domain or data.type in prop.domain:
                    warnings.append(
                        ValidationWarning(
                            code="REQUIRED_PROPERTY_MISSING",
                            message=f"必須プロパティ '{prop.id}' が欠落しています。",
                            field=f"properties.{prop.id}",
                        )
                    )
        return warnings

    def validate_edge(self, data: EdgeCreate) -> list[ValidationWarning]:
        warnings: list[ValidationWarning] = []
        rel = self.ontology.get_relationship(data.predicate)
        if not rel:
            warnings.append(
                ValidationWarning(
                    code="INVALID_RELATIONSHIP",
                    message=f"Relationship '{data.predicate}' はオントロジーに定義されていません。",
                    field="predicate",
                )
            )
            return warnings

        subject = self.graph.get_node(data.subject)
        obj = self.graph.get_node(data.object)
        if not subject:
            warnings.append(
                ValidationWarning(
                    code="SUBJECT_NOT_FOUND",
                    message=f"Subject ノード '{data.subject}' が存在しません。",
                    field="subject",
                )
            )
        if not obj:
            warnings.append(
                ValidationWarning(
                    code="OBJECT_NOT_FOUND",
                    message=f"Object ノード '{data.object}' が存在しません。",
                    field="object",
                )
            )

        if subject and rel.domain and subject.type not in rel.domain:
            warnings.append(
                ValidationWarning(
                    code="DOMAIN_VIOLATION",
                    message=(
                        f"'{data.predicate}' の domain は {', '.join(rel.domain)} です。"
                        f"{subject.type} からの使用はオントロジーと一致しません。"
                    ),
                    field="predicate",
                )
            )

        if obj and rel.range and obj.type not in rel.range:
            warnings.append(
                ValidationWarning(
                    code="RANGE_VIOLATION",
                    message=(
                        f"'{data.predicate}' の range は {', '.join(rel.range)} です。"
                        f"{obj.type} への使用はオントロジーと一致しません。"
                    ),
                    field="object",
                )
            )
        return warnings

    def should_block(self, warnings: list[ValidationWarning]) -> bool:
        return settings.validation_mode == "error" and len(warnings) > 0
