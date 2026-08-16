from dataclasses import dataclass, field

from app.ontology.expressions.class_expression import ClassExpression
from app.ontology.models.resource import Resource


@dataclass
class OwlClass(Resource):
    subclass_of: list[str | ClassExpression] = field(default_factory=list)
    equivalent_class: list[ClassExpression] = field(default_factory=list)
    disjoint_with: list[str | ClassExpression] = field(default_factory=list)
